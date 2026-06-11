const features = [
  "支援上傳或拖曳 JPG / PNG 餐點照片",
  "保留可替換真實模型的 mock AI 架構",
  "可顯示多項食物辨識結果與信心值",
  "每項食物都會估計份量",
  "自動計算總熱量與營養摘要",
  "不使用資料庫也能保留最近分析紀錄",
];

function FeatureGrid() {
  return (
    <section className="feature-section">
      <div className="section-heading">
        <p className="eyebrow">專題亮點</p>
        <h2>以可部署、可展示、可擴充為目標設計</h2>
      </div>
      <div className="feature-grid">
        {features.map((feature) => (
          <article key={feature} className="feature-card">
            <h3>{feature}</h3>
          </article>
        ))}
      </div>
    </section>
  );
}

export default FeatureGrid;
