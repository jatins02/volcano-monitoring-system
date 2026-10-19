import type { ButtonHTMLAttributes, ReactNode } from 'react';
export function DesktopWindow({ id, title, children, tools }: {
    id: string;
    title: string;
    children: ReactNode;
    tools?: ReactNode;
}) {
    return <section id={id} className={`window ${id}`} aria-label={title}>
    <header className="titlebar"><h2>{title}</h2><span aria-hidden="true" className="window-decoration">▱</span></header>
    {tools && <div className="toolbar">{tools}</div>}<div className="workspace">{children}</div>
  </section>;
}
export function RetroButton(props: ButtonHTMLAttributes<HTMLButtonElement>) { return <button type="button" {...props}/>; }
export function MenuBar() { return <nav aria-label="Sections"><strong>VMS / laboratory</strong>{['Simulation', 'Parameters', 'Circuit', 'Assembly', 'Reports'].map(s => <a key={s} href={`#${s.toLowerCase()}`}>{s}</a>)}</nav>; }
export function StatusBar({ children }: {
    children: ReactNode;
}) { return <footer className="statusbar" role="status">{children}</footer>; }
export function StatusLamp({ status }: {
    status?: string;
}) { return <span className={`lamp ${(status ?? 'unknown').toLowerCase()}`}><i aria-hidden="true"/>{status ?? 'NO DATA'}</span>; }
export function PaneTabs<T extends string>({ tabs, value, onChange }: {
    tabs: readonly T[];
    value: T;
    onChange: (tab: T) => void;
}) { return <div className="tabs" role="group" aria-label="Assembly views">{tabs.map(tab => <RetroButton key={tab} aria-pressed={value === tab} onClick={() => onChange(tab)}>{tab}</RetroButton>)}</div>; }
