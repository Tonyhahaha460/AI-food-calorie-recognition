import { Link } from "react-router-dom";

function HeroSection() {
  return (
    <section className="hero-card meal-hero">
      <div className="hero-copy">
        <p className="eyebrow">AI Meal Scanner</p>
        <h1>拍照分析餐點，快速查看卡路里與營養組成</h1>
        <p className="subtitle">
          AI Meal Scanner and Nutrition Analysis Web App 是一個適合大學專題展示的
          React + Flask 網站。使用者可上傳或拍攝食物照片，系統會模擬辨識多項食物、
          估計份量，並回傳總熱量與營養分析結果。
        </p>
        <div className="hero-actions">
          <Link to="/recognition" className="primary-button">
            開始分析
          </Link>
          <Link to="/admin" className="secondary-button">
            編輯食物資料
          </Link>
        </div>
      </div>

      <div className="hero-preview-stack">
        <div className="preview-note">
          <span>多項分析輸出</span>
          <strong>白飯 + 煎蛋 + 沙拉</strong>
        </div>
        <div className="preview-macros">
          <div>
            <span>總熱量</span>
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
