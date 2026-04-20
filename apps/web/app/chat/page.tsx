'use client';

import { useState } from 'react';

export default function ChatPage() {
  const [message, setMessage] = useState('最近墒情怎么样');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [meta, setMeta] = useState<{ intent?: string; answer_type?: string } | null>(null);

  async function submit() {
    setLoading(true);
    try {
      const response = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: 'demo-session', turn_id: 1 })
      });
      const data = await response.json();
      setAnswer(data.final_answer || '暂无回答');
      setMeta({ intent: data.intent, answer_type: data.answer_type });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <div className="card chat-box">
        <div>
          <div className="badge">受限 Flow Agent</div>
          <h1>墒情智能问答</h1>
          <p>当前页面通过 `/api/agent/chat` 调用 Python agent，目标验收对齐 `plans/2` 与 `plans/3`。</p>
        </div>
        <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
        <div className="actions">
          <button className="button" type="button" onClick={submit} disabled={loading}>{loading ? '处理中...' : '发送'}</button>
        </div>
        <div className="card answer">
          <h3>回答</h3>
          <p>{answer || '等待提问...'}</p>
          {meta ? <p><strong>intent:</strong> {meta.intent} · <strong>answer_type:</strong> {meta.answer_type}</p> : null}
        </div>
      </div>
    </main>
  );
}
