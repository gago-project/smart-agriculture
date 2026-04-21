import type { SonioxTemporaryToken } from './sonioxTokenApi';

interface SonioxRealtimeCallbacks {
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
}

function transcriptFromPayload(payload: unknown): string {
  if (!payload || typeof payload !== 'object' || !('tokens' in payload) || !Array.isArray(payload.tokens)) {
    return '';
  }
  return payload.tokens
    .map((token) => {
      if (!token || typeof token !== 'object') return '';
      const value = 'text' in token ? token.text : '';
      return typeof value === 'string' ? value : '';
    })
    .join('');
}

export class SonioxRealtimeClient {
  private readonly onTranscript: SonioxRealtimeCallbacks['onTranscript'];
  private readonly onError: SonioxRealtimeCallbacks['onError'];
  private socket: WebSocket | null = null;
  private recorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;

  constructor({ onTranscript, onError }: SonioxRealtimeCallbacks) {
    this.onTranscript = onTranscript;
    this.onError = onError;
  }

  async start(token: SonioxTemporaryToken): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      throw new Error('无法访问麦克风，请检查浏览器权限');
    }

    await new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(token.websocket_url);
      socket.binaryType = 'arraybuffer';

      socket.onopen = () => {
        this.socket = socket;
        socket.send(
          JSON.stringify({
            api_key: token.api_key,
            model: token.model,
            audio_format: 'auto'
          })
        );

        const recorder = new MediaRecorder(this.stream as MediaStream);
        recorder.ondataavailable = (event) => {
          if (!event.data || event.data.size === 0 || !this.socket || this.socket.readyState !== WebSocket.OPEN) return;
          void event.data.arrayBuffer().then((buffer) => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
              this.socket.send(buffer);
            }
          });
        };
        recorder.start(250);
        this.recorder = recorder;
        resolve();
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data));
          const transcript = transcriptFromPayload(payload);
          if (transcript) {
            this.onTranscript(transcript);
          }
        } catch {
          this.onError('语音识别响应格式异常');
        }
      };

      socket.onerror = () => {
        this.onError('语音识别连接失败');
        reject(new Error('语音识别连接失败'));
      };

      socket.onclose = () => {
        this.socket = null;
      };
    });
  }

  stop(): void {
    if (this.recorder && this.recorder.state !== 'inactive') {
      this.recorder.stop();
    }
    this.recorder = null;

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(new Uint8Array(0));
      this.socket.close();
    } else if (this.socket) {
      this.socket.close();
    }
    this.socket = null;

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
    }
    this.stream = null;
  }
}
