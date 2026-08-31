import React from "react";

type WelcomeBannerProps = {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  className?: string;
};

/** Reusable gradient welcome surface for workspace entry points. */
export default function WelcomeBanner({ eyebrow, title, subtitle, className = "" }: WelcomeBannerProps) {
  return (
    <section className={`shared-welcome-banner ${className}`.trim()}>
      <div className="shared-welcome-banner-content">
        {eyebrow ? <span className="shared-welcome-banner-eyebrow">{eyebrow}</span> : null}
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
    </section>
  );
}
