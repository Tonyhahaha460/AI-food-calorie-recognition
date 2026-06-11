function HistorySection({ items }) {
  return (
    <section className="panel-card">
      <div className="section-heading">
        <p className="eyebrow">分析紀錄</p>
        <h2>最近分析紀錄</h2>
      </div>

      {items.length === 0 ? (
        <p>目前還沒有分析紀錄，先上傳一張餐點照片試試看。</p>
      ) : (
        <div className="history-grid">
          {items.map((item, index) => (
            <article className="history-card" key={`${item.created_at}-${index}`}>
              <div className="history-thumb">
                <img src={item.image_preview} alt="歷史縮圖" className="preview-image" />
              </div>
              <div className="history-meta">
                <strong>{item.total_calories} kcal</strong>
                <span>{new Date(item.created_at).toLocaleString()}</span>
                <small>{item.items.map((food) => food.food_name).join(", ")}</small>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default HistorySection;
