const features = [
  "掃描餐點圖片，快速取得食物名稱與營養數值",
  "AI 信心不足時，可切換手動校正避免錯誤紀錄",
  "每日飲食會整理成熱量、蛋白質、脂肪與碳水狀態",
  "管理端可維護食物資料與訓練圖片",
  "支援會員飲食日誌，方便追蹤每天攝取量",
  "適合專題展示：辨識、查表、紀錄流程完整串接",
];

function FeatureGrid() {
  return (
    <section className="feature-section game-feature-section">
      <div className="section-heading">
        <p className="eyebrow">系統技能</p>
        <h2>不是普通表單，是你的營養冒險介面</h2>
      </div>
      <div className="feature-grid">
        {features.map((feature, index) => (
          <article key={feature} className="feature-card game-skill-card">
            <span className="skill-index">SKILL {String(index + 1).padStart(2, "0")}</span>
            <h3>{feature}</h3>
          </article>
        ))}
      </div>
    </section>
  );
}

export default FeatureGrid;
