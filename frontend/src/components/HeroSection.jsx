import { Link } from "react-router-dom";

function HeroSection() {
  return (
    <section className="hero-card meal-hero game-hero">
      <div className="hero-copy">
        <p className="eyebrow">Nutrition RPG System</p>
        <h1>把每餐變成一場營養任務</h1>
        <p className="subtitle">
          上傳餐點照片，AI 會辨識食物並轉換成熱量、蛋白質、脂肪與碳水數值。辨識失準時也能手動校正，讓你的每日飲食像角色狀態一樣清楚。
        </p>
        <div className="hero-actions">
          <Link to="/recognition" className="primary-button">
            開始掃描
          </Link>
          <Link to="/journal" className="secondary-button">
            查看日誌
          </Link>
        </div>
      </div>

      <div className="hero-preview-stack">
        <div className="preview-note game-status-card">
          <span>今日任務</span>
          <strong>掃描餐點並補滿營養條</strong>
        </div>
        <div className="preview-macros game-stat-grid">
          <div>
            <span>熱量</span>
            <strong>428 kcal</strong>
          </div>
          <div>
            <span>蛋白質</span>
            <strong>16.2 g</strong>
          </div>
          <div>
            <span>脂肪</span>
            <strong>14.8 g</strong>
          </div>
          <div>
            <span>碳水</span>
            <strong>57.6 g</strong>
          </div>
        </div>
      </div>
    </section>
  );
}

export default HeroSection;
