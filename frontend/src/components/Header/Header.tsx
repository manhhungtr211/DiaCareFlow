import './Header.css';

export function Header() {
  return (
    <header className="header" id="app-header">
      <div className="header__inner">
        <div className="header__brand">
          <span className="header__logo" aria-hidden="true">🩺</span>
          <div className="header__text">
            <h1 className="header__title">DiaCareFlow</h1>
            <p className="header__tagline">Hỗ trợ tư vấn tiểu đường thông minh</p>
          </div>
        </div>
        {/*
        <div className="header__status">
          <span className="header__status-dot" />
          <span className="header__status-text">Online</span>
        </div>
        */}
      </div>
    </header>
  );
}
