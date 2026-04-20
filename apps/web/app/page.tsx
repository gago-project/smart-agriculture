import Link from 'next/link';

async function getSummary() {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
    const response = await fetch(`${baseUrl}/api/soil/summary`, { cache: 'no-store' });
    return response.json();
  } catch {
    return { latest_time: '待连接', total_records: 0, risky_devices: 0, avg_water20cm: null };
  }
}

export default async function HomePage() {
  const summary = await getSummary();
  return (
    <main className="page">
      <section className="hero">
        <span className="badge">Smart Agriculture · Soil Moisture Agent</span>
        <h1>智慧农业墒情智能体平台</h1>
        <p>一个 Docker 启动即可运行的前后端一体项目：Next 主应用负责页面、Admin、Soniox 与业务接口；Python Agent 按受限 Flow 负责自然语言理解、真实数据查询、规则判断、预警模板与建议生成。</p>
        <div className="actions">
          <Link className="button" href="/chat">进入智能问答</Link>
          <Link className="button secondary" href="/admin">查看管理后台</Link>
        </div>
      </section>
      <section className="grid">
        <div className="card"><h3>最新业务时间</h3><h2>{summary.latest_time}</h2><p>所有“最近/当前/现在”问题以库内最新业务时间为准。</p></div>
        <div className="card"><h3>墒情样本</h3><h2>{summary.total_records} 条</h2><p>来自独立 MySQL 库 `smart_agriculture`，避免和旧项目混表。</p></div>
        <div className="card"><h3>需关注点位</h3><h2>{summary.risky_devices} 个</h2><p>预警等级由规则引擎判断，LLM 不负责生成事实结论。</p></div>
      </section>
    </main>
  );
}
