import type { SonioxTemporaryToken } from './sonioxTokenApi';

interface SonioxRealtimeCallbacks {
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
}

interface TokensResult {
  finalText: string;
  partialText: string;
}

function parseTokens(payload: unknown): TokensResult {
  if (!payload || typeof payload !== 'object' || !('tokens' in payload) || !Array.isArray(payload.tokens)) {
    return { finalText: '', partialText: '' };
  }
  let finalText = '';
  let partialText = '';
  for (const token of payload.tokens) {
    if (!token || typeof token !== 'object') continue;
    const t = 'text' in token && typeof token.text === 'string' ? token.text : '';
    if ('is_final' in token && token.is_final) {
      finalText += t;
    } else {
      partialText += t;
    }
  }
  return { finalText, partialText };
}

export class SonioxRealtimeClient {
  private readonly onTranscript: SonioxRealtimeCallbacks['onTranscript'];
  private readonly onError: SonioxRealtimeCallbacks['onError'];
  private socket: WebSocket | null = null;
  private recorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private committedText = '';
  private lastFinalText = '';

  constructor({ onTranscript, onError }: SonioxRealtimeCallbacks) {
    this.onTranscript = onTranscript;
    this.onError = onError;
  }

  async start(token: SonioxTemporaryToken): Promise<void> {
    this.committedText = '';
    this.lastFinalText = '';

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      const name = err instanceof Error ? err.name : '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        throw new Error('麦克风权限被拒绝，请点击地址栏左侧的锁图标 → 允许麦克风，然后重试');
      }
      if (name === 'NotFoundError') {
        throw new Error('未找到麦克风设备，请检查是否已连接');
      }
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
            audio_format: 'auto',
            language_hints: ['zh']
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
          const { finalText, partialText } = parseTokens(payload);

          if (finalText || partialText) {
            // Use only is_final tokens for boundary detection:
            // finalText within one utterance grows monotonically and never changes,
            // so a non-startsWith means a new utterance has begun.
            if (this.lastFinalText && !finalText.startsWith(this.lastFinalText)) {
              this.committedText += this.lastFinalText;
            }
            this.lastFinalText = finalText;
            // partialText is live/interim — shown in real time but never committed directly.
            this.onTranscript(this.committedText + finalText + partialText);
          } else if (this.lastFinalText) {
            // Empty message = utterance boundary
            this.committedText += this.lastFinalText;
            this.lastFinalText = '';
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
