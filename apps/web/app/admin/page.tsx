async function getSummary() {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
    const response = await fetch(`${baseUrl}/api/soil/summary`, { cache: 'no-store' });
    return response.json();
  } catch {
    return { latest_time: '待连接', total_records: 0, risky_devices: 0, avg_water20cm: null, devices: [] };
  }
}

export default async function AdminPage() {
  const summary = await getSummary();
  const devices = summary.devices ?? [];
  return (
    <main className="page">
      <div className="card">
        <div className="badge">Admin</div>
        <h1>墒情数据管理概览</h1>
        <p>第一阶段先展示独立库中的设备样例、最新业务时间和规则判断结果，后续再继续补导入、规则编辑、模板管理页面。</p>
        <table className="table">
          <thead>
            <tr>
              <th>设备 SN</th>
              <th>地区</th>
              <th>最新时间</th>
              <th>20cm 含水量</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device: any) => (
              <tr key={device.device_sn}>
                <td>{device.device_sn}</td>
                <td>{device.city_name}{device.county_name}</td>
                <td>{device.record_time}</td>
                <td>{device.water20cm}%</td>
                <td>{device.display_label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
