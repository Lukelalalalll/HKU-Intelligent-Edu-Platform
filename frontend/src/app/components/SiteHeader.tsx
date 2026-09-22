import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../store";
import logoImg from "../../assets/hku_logo.png";
import Breadcrumbs from "../../shared/components/Breadcrumbs";

function SiteHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <div className="site-header-leading">
          <Link className="site-logo" to={user ? (user.role === "teacher" ? "/teacher" : user.role === "student" ? "/student" : "/admin") : "/login"} aria-label="HKU Intelligent Education Platform">
            <img src={logoImg} alt="The University of Hong Kong" />
          </Link>
          {user && <Breadcrumbs />}
        </div>

        <nav className="site-nav" aria-label="主导航">
          {user ? (
            <div className="user-profile">
              <span className="role-pill">{user.role}</span>
              {user.avatar_url ? <img className="avatar avatar-image" src={user.avatar_url} alt="" /> : <span className="avatar" aria-hidden="true">{(user.name || user.username).slice(0, 1).toUpperCase()}</span>}
              <span className="user-name">{user.name || user.username}</span>
              <button className="nav-logout" onClick={handleLogout} type="button">
                <i className="fas fa-sign-out-alt" aria-hidden="true" />
                退出
              </button>
            </div>
          ) : (
            <>
              <Link className="nav-login" to="/login">
                <i className="fas fa-sign-in-alt" aria-hidden="true" />
                登录
              </Link>
              <Link className="nav-register" to="/register">
                <i className="fas fa-user-plus" aria-hidden="true" />
                注册
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}


export default SiteHeader;
