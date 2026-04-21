import { useEffect, useRef, useState } from 'react';
import { SonioxRealtimeClient } from '../services/sonioxRealtime';
import { fetchSonioxTemporaryToken } from '../services/sonioxTokenApi';

interface ComposerProps {
  isSending: boolean;
  onSend: (question: string) => Promise<void>;
}

export function Composer({ isSending, onSend }: ComposerProps) {
  const [value, setValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const clientRef = useRef<SonioxRealtimeClient | null>(null);

  const submit = async () => {
    if (!value.trim() || isSending || isRecording) return;
    const payload = value;
    setValue('');
    await onSend(payload);
  };

  useEffect(() => {
    return () => {
      clientRef.current?.stop();
      clientRef.current = null;
    };
  }, []);

  const startVoiceInput = async () => {
    if (isRecording || isSending) return;
    setVoiceError(null);

    const client = new SonioxRealtimeClient({
      onTranscript: (text) => {
        setValue(text);
      },
      onError: (message) => {
        setVoiceError(message);
        setIsRecording(false);
      }
    });

    try {
      const token = await fetchSonioxTemporaryToken();
      clientRef.current = client;
      await client.start(token);
      setIsRecording(true);
    } catch (error) {
      client.stop();
      clientRef.current = null;
      setVoiceError(error instanceof Error ? error.message : '语音输入启动失败');
      setIsRecording(false);
    }
  };

  const stopVoiceInput = () => {
    clientRef.current?.stop();
    clientRef.current = null;
    setIsRecording(false);
  };

  return (
    <div className="composer-shell">
      <div className="composer-meta">
        <span>直接提问</span>
        <span>{isRecording ? '录音中…再次点击结束' : isSending ? '分析中…' : 'Enter 发送 · Shift+Enter 换行'}</span>
      </div>
      <div className="composer">
        <textarea
          placeholder="例如：最近墒情怎么样？或 按模板输出 SNS00213807 最新预警"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={async (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              await submit();
            }
          }}
        />
        <button
          type="button"
          className={`voice-button${isRecording ? ' recording' : ''}`}
          onClick={isRecording ? stopVoiceInput : () => void startVoiceInput()}
          disabled={isSending}
          aria-label={isRecording ? '停止语音输入' : '开始语音输入'}
          title={isRecording ? '停止语音输入' : '开始语音输入'}
        >
          {isRecording ? '停止录音' : '语音输入'}
        </button>
        <button onClick={submit} disabled={!value.trim() || isSending || isRecording}>
          发送
        </button>
      </div>
      {voiceError ? <div className="composer-error">{voiceError}</div> : null}
    </div>
  );
}
