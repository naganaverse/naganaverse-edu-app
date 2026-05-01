import { useState, useEffect } from "react";
import {
  Home, BookOpen, FolderOpen, BarChart2, User,
  Users, GraduationCap, Bell, Upload, Send,
  CheckCircle, XCircle, Download, FileText,
  ChevronRight, Plus, Star, Zap, Award, Clock,
  TrendingUp, AlertCircle, Check, X,
  ArrowLeft, Video, Paperclip,
  Search, BookMarked, Layers, Target, Flame, MessageSquare,
  Calendar, Shield, Activity, Eye, LogOut,
  ChevronDown, Filter, MoreHorizontal, Sparkles,
  Phone, Hash, UserCheck, TrendingDown, Circle,
  Menu, Moon, Settings, Info, Mail
} from "lucide-react";

/* ─────────── DESIGN TOKENS ─────────── */
const T = {
  ink:      "#0D0D12",
  ink2:     "#1C1C28",
  ink3:     "#2E2E3E",
  slate:    "#6B7280",
  muted:    "#9CA3AF",
  border:   "#E8E8F0",
  surface:  "#F7F7FB",
  white:    "#FFFFFF",
  violet:   "#6C47FF",
  violetL:  "#8B6FFF",
  rose:     "#F43F5E",
  amber:    "#F59E0B",
  emerald:  "#10B981",
  sky:      "#0EA5E9",
  coral:    "#FF6B6B",
  studentC: "#6C47FF",
  teacherC: "#F43F5E",
  ownerC:   "#10B981",
  parentC:  "#0EA5E9",
  adminC:   "#F59E0B",
};

const style = `
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --violet: #6C47FF;
    --violet-l: #8B6FFF;
    --rose: #F43F5E;
    --amber: #F59E0B;
    --emerald: #10B981;
    --sky: #0EA5E9;
    --ink: #0D0D12;
    --ink2: #1C1C28;
    --ink3: #2E2E3E;
    --slate: #6B7280;
    --muted: #9CA3AF;
    --border: #E8E8F0;
    --surface: #F7F7FB;
    --white: #FFFFFF;
    --radius: 20px;
    --radius-sm: 12px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.07);
    --shadow-lg: 0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06);
  }

  body {
    background: #ECEDF5;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    font-family: 'Sora', sans-serif;
  }

  .shell {
    width: 430px;
    height: 100vh;
    max-height: 900px;
    background: var(--surface);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 0 0 1px rgba(0,0,0,0.06), 0 32px 80px rgba(0,0,0,0.22);
    border-radius: 40px;
  }

  .scroll-area {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding-bottom: 88px;
    scrollbar-width: none;
  }
  .scroll-area::-webkit-scrollbar { display: none; }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.92); }
    to   { opacity: 1; transform: scale(1); }
  }
  @keyframes slideRight {
    from { opacity: 0; transform: translateX(-14px); }
    to   { opacity: 1; transform: translateX(0); }
  }
  @keyframes blob {
    0%, 100% { transform: scale(1) rotate(0deg); }
    33%       { transform: scale(1.06) rotate(6deg); }
    66%       { transform: scale(0.96) rotate(-6deg); }
  }
  @keyframes toastSlide {
    from { opacity: 0; transform: translateY(24px) scale(0.96); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }
  @keyframes fadeOverlay {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes slideDrawer {
    from { transform: translateX(-100%); }
    to   { transform: translateX(0); }
  }

  .anim-fadeup  { animation: fadeUp     0.42s cubic-bezier(0.22,1,0.36,1) both; }
  .anim-scale   { animation: scaleIn    0.38s cubic-bezier(0.22,1,0.36,1) both; }
  .anim-slide   { animation: slideRight 0.38s cubic-bezier(0.22,1,0.36,1) both; }

  /* ── ONBOARDING: AUTO SPLASH (LIGHT) ── */
  .splash-auto {
    height: 100%;
    background: var(--white);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 20px;
    position: relative;
    overflow: hidden;
  }
  .splash-auto-blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(72px);
    pointer-events: none;
  }

  .nv-logo-ring {
    width: 100px; height: 100px;
    background: linear-gradient(135deg, var(--violet), #A855F7);
    border-radius: 32px;
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; font-weight: 800; color: white;
    letter-spacing: -1px;
    font-family: 'Sora', sans-serif;
    box-shadow: 0 16px 48px rgba(108,71,255,0.28), 0 0 0 12px rgba(108,71,255,0.07);
    animation: scaleIn 0.5s cubic-bezier(0.22,1,0.36,1) both;
    position: relative; z-index: 1;
  }

  .nv-wordmark {
    font-size: 28px; font-weight: 800; color: var(--ink);
    letter-spacing: -1px;
    animation: fadeUp 0.5s 0.15s cubic-bezier(0.22,1,0.36,1) both;
    position: relative; z-index: 1;
  }
  .nv-wordmark em {
    font-style: normal;
    background: linear-gradient(135deg, var(--violet), #A855F7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .nv-sub {
    font-size: 12px; color: var(--muted); font-weight: 500;
    animation: fadeUp 0.5s 0.25s cubic-bezier(0.22,1,0.36,1) both;
    position: relative; z-index: 1;
  }
  .nv-dot-row {
    display: flex; gap: 6px; margin-top: 8px;
    animation: fadeUp 0.5s 0.35s cubic-bezier(0.22,1,0.36,1) both;
    position: relative; z-index: 1;
  }
  .nv-dot {
    width: 6px; height: 6px; border-radius: 50%;
  }

  /* ── ONBOARDING: LOGIN ── */
  .login-screen {
    height: 100%;
    background: white;
    display: flex;
    flex-direction: column;
    padding: 56px 28px 32px;
    position: relative;
    overflow: hidden;
  }

  .login-icon-box {
    width: 72px; height: 72px;
    background: linear-gradient(135deg, #F3EEFF, #EFF6FF);
    border-radius: 24px;
    display: flex; align-items: center; justify-content: center;
    border: 1px solid var(--border);
    margin-bottom: 28px;
    animation: scaleIn 0.45s cubic-bezier(0.22,1,0.36,1) both;
  }

  .login-heading {
    font-size: 24px; font-weight: 800; color: var(--ink);
    letter-spacing: -0.6px; line-height: 1.2;
    margin-bottom: 8px;
    animation: fadeUp 0.45s 0.08s cubic-bezier(0.22,1,0.36,1) both;
  }

  .login-sub {
    font-size: 13px; color: var(--muted); font-weight: 500;
    margin-bottom: 36px; line-height: 1.5;
    animation: fadeUp 0.45s 0.12s cubic-bezier(0.22,1,0.36,1) both;
  }

  .phone-input-group {
    display: flex; gap: 10px; margin-bottom: 20px;
    animation: fadeUp 0.45s 0.16s cubic-bezier(0.22,1,0.36,1) both;
  }

  .country-selector {
    display: flex; align-items: center; gap: 6px;
    padding: 0 14px;
    border-radius: 14px;
    border: 1.5px solid var(--border);
    background: var(--surface);
    font-family: 'Sora', sans-serif;
    font-size: 13px; font-weight: 700; color: var(--ink);
    cursor: pointer; white-space: nowrap;
    height: 52px;
    transition: border-color 0.2s;
  }
  .country-selector:hover { border-color: var(--violet); }

  .phone-input {
    flex: 1;
    padding: 0 16px;
    height: 52px;
    border-radius: 14px;
    border: 1.5px solid var(--border);
    background: white;
    font-family: 'Sora', sans-serif;
    font-size: 16px; font-weight: 600; color: var(--ink);
    outline: none;
    transition: border-color 0.2s;
    letter-spacing: 1px;
  }
  .phone-input:focus { border-color: var(--violet); }
  .phone-input::placeholder { color: var(--muted); font-weight: 500; letter-spacing: 0; font-size: 14px; }

  .login-continue-btn {
    animation: fadeUp 0.45s 0.2s cubic-bezier(0.22,1,0.36,1) both;
  }

  .login-footer {
    position: absolute;
    bottom: 32px; left: 28px; right: 28px;
    text-align: center;
    font-size: 11px; color: var(--muted); font-weight: 500;
    line-height: 1.6;
    animation: fadeUp 0.45s 0.28s cubic-bezier(0.22,1,0.36,1) both;
  }
  .login-footer a { color: var(--violet); font-weight: 700; cursor: pointer; text-decoration: none; }

  /* ── ROLE SELECTION ── */
  .splash {
    height: 100%;
    background: var(--ink);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 36px 28px;
    position: relative;
    overflow: hidden;
    gap: 0;
  }

  .splash-blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(56px);
    animation: blob 7s ease-in-out infinite;
    pointer-events: none;
  }

  .splash-logo-wrap {
    position: relative;
    margin-bottom: 28px;
    animation: scaleIn 0.6s cubic-bezier(0.22,1,0.36,1) both;
  }

  .splash-logo-bg {
    width: 96px; height: 96px;
    background: linear-gradient(135deg, var(--violet), #A855F7);
    border-radius: 30px;
    display: flex; align-items: center; justify-content: center;
    font-size: 40px;
    box-shadow: 0 12px 40px rgba(108,71,255,0.5), 0 0 0 1px rgba(255,255,255,0.1);
  }

  .splash-brand {
    animation: fadeUp 0.6s 0.1s cubic-bezier(0.22,1,0.36,1) both;
    text-align: center;
    margin-bottom: 10px;
  }

  .splash-title {
    font-size: 32px; font-weight: 800; color: white;
    letter-spacing: -1px; line-height: 1;
  }
  .splash-title em {
    font-style: normal;
    background: linear-gradient(135deg, #A78BFA, #F472B6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .splash-tagline {
    font-size: 12px; color: rgba(255,255,255,0.42);
    font-weight: 500; letter-spacing: 0.5px; margin-top: 6px;
  }

  .role-prompt {
    font-size: 11px; font-weight: 600;
    color: rgba(255,255,255,0.32);
    letter-spacing: 2.5px; text-transform: uppercase;
    margin-bottom: 18px;
    animation: fadeUp 0.5s 0.2s both;
  }

  .role-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 12px; width: 100%;
    animation: fadeUp 0.5s 0.25s both;
  }

  .role-tile {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 22px; padding: 22px 14px 18px;
    text-align: center; cursor: pointer;
    transition: transform 0.22s cubic-bezier(0.22,1,0.36,1), border-color 0.2s, background 0.2s;
    position: relative; overflow: hidden;
    backdrop-filter: blur(12px);
  }
  .role-tile:active { transform: scale(0.96); }
  .role-tile:hover { transform: translateY(-4px); border-color: rgba(255,255,255,0.2); background: rgba(255,255,255,0.08); }

  .role-tile-glow {
    position: absolute; inset: 0; opacity: 0;
    transition: opacity 0.25s; border-radius: 22px;
  }
  .role-tile:hover .role-tile-glow { opacity: 1; }

  .role-emoji { font-size: 28px; margin-bottom: 10px; display: block; filter: drop-shadow(0 4px 10px rgba(0,0,0,0.25)); }
  .role-tile-name { font-size: 13px; font-weight: 700; color: white; letter-spacing: -0.2px; }
  .role-tile-sub { font-size: 10px; color: rgba(255,255,255,0.38); margin-top: 3px; font-weight: 500; }

  /* ── BOTTOM NAV ── */
  .bottom-nav {
    position: absolute; bottom: 0; left: 0; right: 0;
    height: 80px;
    background: rgba(255,255,255,0.94);
    backdrop-filter: blur(20px);
    border-top: 1px solid rgba(0,0,0,0.06);
    display: flex; align-items: center;
    padding: 0 12px 8px; z-index: 50;
  }

  .nav-btn {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; gap: 4px; cursor: pointer;
    padding: 8px 4px; border-radius: 14px;
    transition: all 0.22s cubic-bezier(0.22,1,0.36,1);
  }

  .nav-pip {
    width: 32px; height: 32px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.25s cubic-bezier(0.34,1.56,0.64,1);
  }
  .nav-btn.active .nav-pip { background: var(--ink); transform: scale(1.08) translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,0.2); }
  .nav-btn.active svg { color: white !important; }
  .nav-btn:not(.active) svg { color: var(--muted); }

  .nav-lbl { font-size: 9.5px; font-weight: 600; letter-spacing: 0.2px; }
  .nav-btn.active .nav-lbl { color: var(--ink); }
  .nav-btn:not(.active) .nav-lbl { color: var(--muted); }

  /* ── SHARED ── */
  .topbar { display: flex; align-items: center; justify-content: space-between; padding: 20px 20px 0; }
  .page-title { font-size: 22px; font-weight: 800; color: var(--ink); letter-spacing: -0.6px; }

  .avatar-chip {
    width: 42px; height: 42px; border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 13px; color: white;
    flex-shrink: 0; cursor: pointer; transition: transform 0.2s;
  }
  .avatar-chip:hover { transform: scale(1.06); }

  .notif-dot {
    width: 36px; height: 36px; background: var(--surface);
    border-radius: 12px; display: flex; align-items: center; justify-content: center;
    position: relative; cursor: pointer; border: 1px solid var(--border);
  }
  .notif-badge {
    position: absolute; top: 6px; right: 6px;
    width: 7px; height: 7px; background: var(--rose);
    border-radius: 50%; border: 1.5px solid white;
  }

  .hero { margin: 16px 20px 0; border-radius: 26px; padding: 24px 22px; position: relative; overflow: hidden; }

  .hero-chip {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,255,255,0.18); color: rgba(255,255,255,0.9);
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; padding: 4px 10px; border-radius: 20px;
    margin-bottom: 12px; backdrop-filter: blur(8px);
  }

  .hero-h { font-size: 24px; font-weight: 800; color: white; line-height: 1.15; letter-spacing: -0.6px; margin-bottom: 8px; }
  .hero-p { font-size: 12px; color: rgba(255,255,255,0.65); margin-bottom: 20px; line-height: 1.5; }
  .hero-stats { display: flex; gap: 10px; }

  .hero-stat {
    background: rgba(255,255,255,0.14); border-radius: 14px;
    padding: 10px 14px; backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.12);
  }
  .hero-stat-n { font-size: 20px; font-weight: 800; color: white; letter-spacing: -0.5px; font-family: 'Space Mono', monospace; }
  .hero-stat-l { font-size: 9px; color: rgba(255,255,255,0.55); font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 2px; }
  .hero-orb { position: absolute; border-radius: 50%; background: rgba(255,255,255,0.1); pointer-events: none; }

  .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 16px 20px 0; }
  .stat-tile { border-radius: 22px; padding: 18px 16px; position: relative; overflow: hidden; cursor: pointer; transition: transform 0.22s, box-shadow 0.22s; }
  .stat-tile:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
  .stat-tile-icon { width: 36px; height: 36px; background: rgba(255,255,255,0.22); border-radius: 11px; display: flex; align-items: center; justify-content: center; margin-bottom: 14px; }
  .stat-tile-n { font-size: 28px; font-weight: 800; color: white; letter-spacing: -1px; font-family: 'Space Mono', monospace; line-height: 1; }
  .stat-tile-l { font-size: 11px; color: rgba(255,255,255,0.7); font-weight: 600; margin-top: 5px; }
  .stat-tile-badge { position: absolute; top: 14px; right: 14px; background: rgba(255,255,255,0.22); color: white; font-size: 9px; font-weight: 800; padding: 3px 8px; border-radius: 20px; font-family: 'Space Mono', monospace; }

  .actions-row { display: flex; gap: 10px; overflow-x: auto; padding: 0 20px; scrollbar-width: none; }
  .actions-row::-webkit-scrollbar { display: none; }
  .action-pill { flex-shrink: 0; display: flex; flex-direction: column; align-items: center; gap: 7px; cursor: pointer; }
  .action-pip { width: 58px; height: 58px; border-radius: 20px; display: flex; align-items: center; justify-content: center; transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1); box-shadow: 0 4px 16px rgba(0,0,0,0.13); }
  .action-pill:hover .action-pip { transform: scale(1.1) translateY(-3px); }
  .action-pill:active .action-pip { transform: scale(0.95); }
  .action-lbl { font-size: 10px; font-weight: 700; color: var(--ink3); text-align: center; max-width: 60px; line-height: 1.2; }

  .sec { padding: 20px 20px 0; }
  .sec-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
  .sec-title { font-size: 15px; font-weight: 800; color: var(--ink); letter-spacing: -0.3px; }
  .sec-link { font-size: 11px; font-weight: 700; color: var(--violet); cursor: pointer; }

  .card { background: white; border-radius: var(--radius); padding: 16px; margin-bottom: 10px; box-shadow: var(--shadow); cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; border: 1px solid var(--border); }
  .card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }

  .card-row { background: white; border-radius: var(--radius); padding: 14px 16px; margin-bottom: 9px; display: flex; align-items: center; gap: 12px; box-shadow: var(--shadow); cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; border: 1px solid var(--border); }
  .card-row:hover { transform: translateX(3px); box-shadow: var(--shadow-lg); }

  .avatar { border-radius: 14px; display: flex; align-items: center; justify-content: center; font-weight: 800; color: white; flex-shrink: 0; font-size: 13px; }

  .pbar-wrap { height: 4px; background: var(--border); border-radius: 4px; overflow: hidden; margin-top: 8px; }
  .pbar-fill { height: 100%; border-radius: 4px; transition: width 0.9s cubic-bezier(0.22,1,0.36,1); }

  .pill { display: inline-flex; align-items: center; padding: 3px 9px; border-radius: 20px; font-size: 10px; font-weight: 800; }
  .pill-green  { background: #ECFDF5; color: #059669; }
  .pill-amber  { background: #FFFBEB; color: #D97706; }
  .pill-red    { background: #FFF1F2; color: #E11D48; }
  .pill-violet { background: #F3EEFF; color: #6C47FF; }
  .pill-sky    { background: #F0F9FF; color: #0284C7; }

  .chip-row { display: flex; gap: 7px; overflow-x: auto; padding: 0 20px; scrollbar-width: none; }
  .chip-row::-webkit-scrollbar { display: none; }
  .chip { flex-shrink: 0; padding: 7px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s; border: 1.5px solid transparent; }
  .chip.on  { color: white; border-color: transparent; box-shadow: 0 3px 12px rgba(0,0,0,0.16); }
  .chip.off { background: white; color: var(--muted); border-color: var(--border); }
  .chip.off:hover { border-color: var(--violet); color: var(--violet); }

  .file-row { background: white; border-radius: 16px; padding: 13px 15px; display: flex; align-items: center; gap: 11px; margin-bottom: 8px; box-shadow: var(--shadow); cursor: pointer; border: 1px solid var(--border); transition: transform 0.2s; }
  .file-row:hover { transform: translateX(3px); }
  .file-ico { width: 42px; height: 42px; border-radius: 13px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

  .hw-card { background: white; border-radius: var(--radius); padding: 15px; margin-bottom: 10px; border-left: 3.5px solid transparent; box-shadow: var(--shadow); cursor: pointer; border: 1px solid var(--border); transition: transform 0.2s; }
  .hw-card:hover { transform: translateY(-2px); }

  .ann-card { border-radius: 24px; padding: 20px; margin-bottom: 12px; position: relative; overflow: hidden; cursor: pointer; }

  .att-row { background: white; border-radius: 16px; padding: 13px 15px; display: flex; align-items: center; gap: 11px; margin-bottom: 8px; border: 1px solid var(--border); box-shadow: var(--shadow); transition: all 0.2s; }
  .att-btn { padding: 6px 14px; border-radius: 10px; border: none; font-size: 11px; font-weight: 800; cursor: pointer; transition: all 0.2s cubic-bezier(0.34,1.56,0.64,1); font-family: 'Sora', sans-serif; }
  .att-p     { background: #ECFDF5; color: #059669; }
  .att-p.on  { background: #10B981; color: white; box-shadow: 0 3px 10px rgba(16,185,129,0.4); transform: scale(1.05); }
  .att-a     { background: #FFF1F2; color: #E11D48; }
  .att-a.on  { background: #F43F5E; color: white; box-shadow: 0 3px 10px rgba(244,63,94,0.4); transform: scale(1.05); }

  .ring-wrap { position: relative; display: inline-block; }
  .ring-val { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); font-weight: 800; font-family: 'Space Mono', monospace; color: var(--ink); }

  .upload-zone { border: 2px dashed var(--border); border-radius: 22px; padding: 38px 20px; text-align: center; cursor: pointer; background: white; transition: all 0.2s; }
  .upload-zone:hover, .upload-zone.drag { border-color: var(--violet); background: #F5F0FF; }
  .upload-pip { width: 68px; height: 68px; background: linear-gradient(135deg, var(--violet), #A855F7); border-radius: 22px; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; box-shadow: 0 8px 24px rgba(108,71,255,0.3); }

  .field-label { font-size: 10px; font-weight: 700; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }

  .custom-select, .custom-input { width: 100%; padding: 12px 15px; border-radius: 14px; border: 1.5px solid var(--border); background: white; font-family: 'Sora', sans-serif; font-size: 13px; color: var(--ink); outline: none; transition: border-color 0.2s; margin-bottom: 13px; }
  .custom-select:focus, .custom-input:focus { border-color: var(--violet); }

  .btn-primary { width: 100%; padding: 14px; border-radius: 16px; border: none; background: var(--ink); color: white; font-family: 'Sora', sans-serif; font-weight: 700; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s; letter-spacing: -0.2px; }
  .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.22); }
  .btn-primary:active { transform: scale(0.98); }

  .btn-accent { width: 100%; padding: 14px; border-radius: 16px; border: none; background: linear-gradient(135deg, var(--violet), #A855F7); color: white; font-family: 'Sora', sans-serif; font-weight: 700; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s; box-shadow: 0 6px 20px rgba(108,71,255,0.32); }
  .btn-accent:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(108,71,255,0.42); }
  .btn-accent:active { transform: scale(0.98); }

  .toast { position: absolute; bottom: 92px; left: 16px; right: 16px; background: var(--ink); border-radius: 18px; padding: 14px 16px; display: flex; align-items: center; gap: 12px; z-index: 999; box-shadow: 0 8px 32px rgba(0,0,0,0.3); animation: toastSlide 0.38s cubic-bezier(0.22,1,0.36,1) both; border: 1px solid rgba(255,255,255,0.07); }
  .toast-ico { width: 34px; height: 34px; border-radius: 11px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .toast-title { font-weight: 700; font-size: 13px; color: white; }
  .toast-sub   { font-size: 11px; color: rgba(255,255,255,0.5); margin-top: 1px; }

  .profile-hero-bg { background: var(--ink); padding: 36px 20px 44px; position: relative; overflow: hidden; }
  .profile-av { width: 76px; height: 76px; border-radius: 24px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 26px; color: white; margin-bottom: 14px; border: 2px solid rgba(255,255,255,0.14); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
  .profile-name-text { font-size: 22px; font-weight: 800; color: white; letter-spacing: -0.6px; }
  .profile-role-text { font-size: 12px; color: rgba(255,255,255,0.45); margin-top: 3px; }
  .profile-badge-wrap { display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.1); padding: 5px 12px; border-radius: 20px; margin-top: 10px; color: var(--amber); font-size: 11px; font-weight: 700; }

  .menu-row { display: flex; align-items: center; gap: 14px; padding: 15px 20px; cursor: pointer; transition: background 0.2s; border-bottom: 1px solid var(--surface); }
  .menu-row:hover { background: var(--surface); }
  .menu-ico { width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .menu-lbl { font-weight: 700; font-size: 13.5px; color: var(--ink); flex: 1; }

  .empty { text-align: center; padding: 48px 32px; }
  .empty-ico { width: 72px; height: 72px; background: var(--surface); border-radius: 24px; display: flex; align-items: center; justify-content: center; margin: 0 auto 18px; border: 1px solid var(--border); }

  .class-row { background: white; border-radius: var(--radius); padding: 15px; display: flex; align-items: center; gap: 12px; margin-bottom: 9px; box-shadow: var(--shadow); cursor: pointer; border: 1px solid var(--border); transition: transform 0.2s; }
  .class-row:hover { transform: translateX(4px); }
  .class-time-box { background: var(--surface); border-radius: 12px; padding: 8px 11px; text-align: center; flex-shrink: 0; border: 1px solid var(--border); min-width: 54px; }

  .hw-preview { background: linear-gradient(135deg, #F5F0FF, #EFF6FF); border-radius: 18px; padding: 18px; margin-top: 14px; border: 1.5px dashed rgba(108,71,255,0.3); animation: scaleIn 0.35s cubic-bezier(0.22,1,0.36,1) both; }
  .hw-q { background: white; border-radius: 11px; padding: 10px 13px; font-size: 12px; color: var(--ink); margin-bottom: 7px; border-left: 3px solid var(--violet); font-weight: 500; line-height: 1.4; }

  .child-card { background: var(--ink); border-radius: 26px; padding: 22px; margin: 16px 20px 0; position: relative; overflow: hidden; }
  .subject-att-row { background: white; border-radius: 16px; padding: 14px 16px; display: flex; align-items: center; gap: 12px; margin-bottom: 8px; border: 1px solid var(--border); box-shadow: var(--shadow); }

  /* ── SIDE DRAWER ── */
  .drawer-overlay {
    position: absolute; inset: 0;
    background: rgba(0,0,0,0.45);
    z-index: 200;
    animation: fadeOverlay 0.25s ease both;
    border-radius: 40px;
  }
  .side-drawer {
    position: absolute;
    top: 0; bottom: 0; left: 0;
    width: 288px;
    background: white;
    z-index: 201;
    display: flex;
    flex-direction: column;
    animation: slideDrawer 0.32s cubic-bezier(0.22,1,0.36,1) both;
    border-radius: 40px 28px 28px 40px;
    box-shadow: 8px 0 48px rgba(0,0,0,0.18);
    overflow: hidden;
  }
  .drawer-header {
    padding: 48px 24px 24px;
    background: linear-gradient(145deg, var(--ink), #2D1060);
    position: relative; overflow: hidden;
  }
  .drawer-item {
    display: flex; align-items: center; gap: 14px;
    padding: 14px 20px; cursor: pointer;
    transition: background 0.18s;
    border-bottom: 1px solid var(--surface);
  }
  .drawer-item:hover { background: var(--surface); }
  .drawer-item-ico {
    width: 38px; height: 38px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  .drawer-item-lbl { font-weight: 700; font-size: 13.5px; color: var(--ink); flex: 1; }
  .drawer-footer { padding: 16px 20px; margin-top: auto; border-top: 1px solid var(--border); }

  /* ── STUDENT GROUP TOGGLE ── */
  .group-toggle-wrap {
    display: flex;
    background: var(--surface);
    border-radius: 14px;
    padding: 3px;
    border: 1px solid var(--border);
  }
  .group-toggle-btn {
    flex: 1; padding: 7px 10px;
    border-radius: 11px; font-size: 12px; font-weight: 700;
    cursor: pointer; text-align: center;
    transition: all 0.22s cubic-bezier(0.22,1,0.36,1);
    border: none; font-family: 'Sora', sans-serif;
  }

  /* ── STUDENT PROFILE CARD ── */
  .sp-contact-row {
    display: flex; align-items: center; gap: 12px;
  }
  .sp-action-btn {
    width: 38px; height: 38px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    text-decoration: none; flex-shrink: 0;
    transition: transform 0.2s;
  }
  .sp-action-btn:hover { transform: scale(1.1); }

  @media (max-width: 440px) {
    .shell { width: 100vw; border-radius: 0; max-height: 100vh; }
    .drawer-overlay { border-radius: 0; }
    .side-drawer { border-radius: 0 28px 28px 0; }
  }
`;

/* ─── DATA ─── */
const classesList = ["Class 10", "Class 11", "Class 12", "Dropper"];
const batchesList = ["Foundation Batch", "JEE Mains Batch", "JEE Adv. Batch A", "NEET Batch B"];

const students = [
  { id: 1, name: "Aryan Sharma",  class: "Class 11", batch: "JEE Adv. Batch A",  roll: "001", att: 88, fee: "paid",    init: "AS", color: T.violet,  image: null, parents: { father: "Ramesh Sharma",  mother: "Priya Sharma",  phone: "9876543210", whatsapp: "9876543210", email: "ramesh@example.com" } },
  { id: 2, name: "Ankit Mugesh",  class: "Class 11", batch: "JEE Mains Batch",   roll: "042", att: 75, fee: "pending", init: "AM", color: T.rose,    image: null, parents: { father: "Mukesh Kumar",   mother: "Anita Devi",    phone: "9876543211", whatsapp: "9876543211", email: "mukesh@example.com" } },
  { id: 3, name: "Ankit Mugesh",  class: "Class 12", batch: "NEET Batch B",       roll: "018", att: 92, fee: "paid",    init: "AM", color: T.emerald, image: "https://i.pravatar.cc/150?u=ankit", parents: { father: "Rajesh Mugesh",  mother: "Sunita Mugesh", phone: "9876543212", whatsapp: "9876543212", email: "rajesh@example.com" } },
  { id: 4, name: "Adarsh",        class: "Class 12", batch: "JEE Adv. Batch A",  roll: "007", att: 85, fee: "paid",    init: "AD", color: T.sky,     image: null, parents: { father: "Vikram Singh",   mother: "Meena Singh",   phone: "9876543213", whatsapp: "9876543213", email: "vikram@example.com" } },
  { id: 5, name: "Priya Patel",   class: "Class 12", batch: "NEET Batch B",       roll: "022", att: 72, fee: "overdue", init: "PP", color: T.amber,   image: null, parents: { father: "Suresh Patel",   mother: "Kavita Patel",  phone: "9876543214", whatsapp: "9876543214", email: "suresh@example.com" } },
];

const todaysClasses = [
  { id: 1, time: "9:00",  per: "AM", name: "Physics – Optics",        batch: "JEE Adv. Batch A", status: "ongoing",  color: T.violet },
  { id: 2, time: "11:00", per: "AM", name: "Chemistry – Organic",     batch: "NEET Batch B",      status: "upcoming", color: T.rose },
  { id: 3, time: "2:00",  per: "PM", name: "Math – Calculus",         batch: "JEE Mains Batch",  status: "upcoming", color: T.emerald },
  { id: 4, time: "4:30",  per: "PM", name: "Physics – Doubt Session", batch: "All Batches",       status: "upcoming", color: T.amber },
];

const homeworkList = [
  { id: 1, subject: "Physics",   topic: "Newton's Laws – Numericals",  due: "Tomorrow", color: T.violet },
  { id: 2, subject: "Chemistry", topic: "Organic Reactions Worksheet", due: "2 days",   color: T.rose },
  { id: 3, subject: "Math",      topic: "Integration by Parts",        due: "Today",    color: T.amber },
];

const subjects = [
  { name: "All",       color: T.violet,  bg: "#F3EEFF", icon: "📚", files: 42 },
  { name: "Physics",   color: T.violet,  bg: "#F3EEFF", icon: "⚡", files: 14 },
  { name: "Chemistry", color: T.rose,    bg: "#FFF1F2", icon: "🧪", files: 11 },
  { name: "Math",      color: T.emerald, bg: "#ECFDF5", icon: "📐", files: 9  },
  { name: "Biology",   color: T.amber,   bg: "#FFFBEB", icon: "🧬", files: 6  },
  { name: "English",   color: T.sky,     bg: "#F0F9FF", icon: "✏️",  files: 2  },
];

const files = [
  { id: 1, name: "Kinematics Notes",      type: "pdf",   size: "2.4 MB", date: "Mar 8", subject: "Physics",   color: T.violet,  bg: "#F3EEFF" },
  { id: 2, name: "Organic Chemistry PDF", type: "pdf",   size: "3.1 MB", date: "Mar 7", subject: "Chemistry", color: T.rose,    bg: "#FFF1F2" },
  { id: 3, name: "Integration Practice",  type: "doc",   size: "1.2 MB", date: "Mar 6", subject: "Math",      color: T.emerald, bg: "#ECFDF5" },
  { id: 4, name: "Cell Division Video",   type: "video", size: "45 MB",  date: "Mar 5", subject: "Biology",   color: T.amber,   bg: "#FFFBEB" },
  { id: 5, name: "Grammar Worksheet",     type: "doc",   size: "0.8 MB", date: "Mar 4", subject: "English",   color: T.sky,     bg: "#F0F9FF" },
];

const announcements = [
  { id: 1, title: "Unit Test Next Week!", body: "Chapters 3–5, Physics. Bring calculator and scientific tables. Starts 9 AM sharp.", time: "2h ago",    grad: `linear-gradient(135deg, ${T.violet}, #A855F7)`,  icon: "📢" },
  { id: 2, title: "PTM on Saturday",      body: "Parent-Teacher Meeting Saturday 10 AM – 1 PM. All parents requested to attend.",    time: "Yesterday", grad: `linear-gradient(135deg, ${T.rose}, #FB923C)`,    icon: "🏫" },
  { id: 3, title: "Holiday – Holi 🎨",   body: "Institute closed March 14th. Classes resume March 15th as scheduled.",              time: "2 days ago", grad: `linear-gradient(135deg, ${T.emerald}, #22D3EE)`, icon: "🎉" },
];

const hwQs = {
  Physics:   ["A ball dropped from 20m height. Find time to reach ground.", "Define Newton's 3rd law with 2 real-life examples.", "5kg object at 3m/s. Calculate kinetic energy."],
  Chemistry: ["Draw structural formula of Ethanol.", "Explain SN1 vs SN2 reaction mechanism.", "Name the reagent used in Clemmensen reduction."],
  Math:      ["Integrate: ∫ x²·eˣ dx using integration by parts.", "Find area under y = x² from x=0 to x=3.", "Solve the differential equation: dy/dx = 2xy."],
};

const parentSubjectAtt = [
  { subj: "Physics",   pct: 88, color: T.violet,  bg: "#F3EEFF" },
  { subj: "Chemistry", pct: 76, color: T.rose,    bg: "#FFF1F2" },
  { subj: "Math",      pct: 92, color: T.emerald, bg: "#ECFDF5" },
  { subj: "Biology",   pct: 65, color: T.amber,   bg: "#FFFBEB" },
];

/* ─── SMALL COMPONENTS ─── */
const Ring = ({ v, color, size = 68 }) => {
  const r = (size - 10) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={T.border} strokeWidth={6} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={6}
        strokeDasharray={c} strokeDashoffset={c - (v/100)*c}
        strokeLinecap="round" style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(0.22,1,0.36,1)" }} />
    </svg>
  );
};

const Toast = ({ msg, sub, color, onClose }) => (
  <div className="toast">
    <div className="toast-ico" style={{ background: color }}><Check size={16} color="white" /></div>
    <div style={{ flex: 1 }}>
      <div className="toast-title">{msg}</div>
      {sub && <div className="toast-sub">{sub}</div>}
    </div>
    <div onClick={onClose} style={{ cursor: "pointer", color: "rgba(255,255,255,0.3)" }}><X size={15} /></div>
  </div>
);

const FeePill = ({ fee }) => {
  const map = { paid: ["pill-green", "Paid"], pending: ["pill-amber", "Pending"], overdue: ["pill-red", "Overdue"] };
  const [cls, lbl] = map[fee] || ["pill-violet", fee];
  return <span className={`pill ${cls}`}>{lbl}</span>;
};

const FileIco = ({ type }) => {
  if (type === "video") return <Video size={18} />;
  if (type === "pdf")   return <FileText size={18} />;
  return <Paperclip size={18} />;
};

const roles = {
  student: { name: "Aryan Sharma",   init: "AS", color: T.studentC, sub: "Class 11 · JEE Adv.",   badge: "JEE Aspirant 🚀" },
  teacher: { name: "Dr. Amit Kumar", init: "AK", color: T.teacherC, sub: "Physics Faculty",        badge: "5★ Teacher ⭐" },
  owner:   { name: "Rajesh Nagana",  init: "RN", color: T.ownerC,   sub: "Institute Director",     badge: "Owner 👑" },
  parent:  { name: "Ramesh Sharma",  init: "RS", color: T.parentC,  sub: "Parent · Aryan Sharma",  badge: "Parent 👨‍👧" },
};

/* ═══════════════════════════════════════
   MAIN APP
═══════════════════════════════════════ */
export default function App() {
  const [appView, setAppView]               = useState("splash");
  const [role, setRole]                     = useState(null);
  const [tab, setTab]                       = useState("home");
  const [toast, setToast]                   = useState(null);
  const [att, setAtt]                       = useState({});
  const [activeSub, setActiveSub]           = useState("All");
  const [hwBatch, setHwBatch]               = useState("JEE Adv. Batch A");
  const [hwSubj, setHwSubj]                 = useState("Physics");
  const [hwPreview, setHwPreview]           = useState(false);
  const [uploaded, setUploaded]             = useState(false);
  const [dragging, setDragging]             = useState(false);
  const [phone, setPhone]                   = useState("");
  const [drawerOpen, setDrawerOpen]         = useState(false);
  const [darkMode, setDarkMode]             = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);

  /* Auto-advance splash → login */
  useEffect(() => {
    if (appView === "splash") {
      const t = setTimeout(() => setAppView("login"), 2200);
      return () => clearTimeout(t);
    }
  }, [appView]);

  const showToast = (msg, sub = "", color = T.violet) => {
    setToast({ msg, sub, color });
    setTimeout(() => setToast(null), 2800);
  };

  const toggleAtt = (id, v) => setAtt(p => ({ ...p, [id]: p[id] === v ? null : v }));

  const handleTabChange = (id) => {
    setSelectedStudent(null);
    setTab(id);
  };

  /* ══════════════════════════════════════
     SCREEN 1 — LIGHT AUTO SPLASH
  ══════════════════════════════════════ */
  if (appView === "splash") {
    return (
      <>
        <style>{style}</style>
        <div className="shell">
          <div className="splash-auto">
            {/* Soft decorative blobs */}
            <div className="splash-auto-blob" style={{ width:280, height:280, background:"rgba(108,71,255,0.10)", top:-100, right:-80 }} />
            <div className="splash-auto-blob" style={{ width:200, height:200, background:"rgba(168,85,247,0.08)", bottom:40, left:-60 }} />
            <div className="splash-auto-blob" style={{ width:140, height:140, background:"rgba(14,165,233,0.06)", top:"40%", right:"5%" }} />

            <div className="nv-logo-ring">NV</div>

            <div style={{ textAlign:"center", position:"relative", zIndex:1 }}>
              <div className="nv-wordmark">Nagana<em>verse</em></div>
              <div className="nv-sub" style={{ marginTop:6 }}>Redefining Coaching Education</div>
            </div>

            <div className="nv-dot-row">
              <div className="nv-dot" style={{ background:T.violet, opacity:0.9 }} />
              <div className="nv-dot" style={{ background:T.violetL, opacity:0.5 }} />
              <div className="nv-dot" style={{ background:T.border, opacity:0.8 }} />
            </div>
          </div>
        </div>
      </>
    );
  }

  /* ══════════════════════════════════════
     SCREEN 2 — MOBILE LOGIN
  ══════════════════════════════════════ */
  if (appView === "login") {
    const handleContinue = () => {
      if (phone.length === 10) {
        setAppView("roles");
      } else {
        showToast("Invalid number", "Enter a valid 10-digit number", T.rose);
      }
    };

    return (
      <>
        <style>{style}</style>
        <div className="shell">
          <div className="login-screen">
            <div className="login-icon-box">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
                stroke={T.violet} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="5" y="2" width="14" height="20" rx="2" />
                <circle cx="12" cy="17" r="1" fill={T.violet} stroke="none" />
              </svg>
            </div>

            <div className="login-heading">Please Enter Your<br />Mobile Number</div>
            <div className="login-sub">We'll send a verification code<br />to confirm your identity.</div>

            <div className="phone-input-group">
              <div className="country-selector">
                <span>🇮🇳</span>
                <span>+91</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                  stroke={T.muted} strokeWidth="2.5" strokeLinecap="round">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </div>
              <input
                className="phone-input"
                type="tel"
                inputMode="numeric"
                maxLength={10}
                placeholder="Enter mobile number"
                value={phone}
                onChange={e => setPhone(e.target.value.replace(/\D/g, ""))}
                onKeyDown={e => e.key === "Enter" && handleContinue()}
              />
            </div>

            <div className="login-continue-btn">
              <button className="btn-accent" onClick={handleContinue}>
                Continue
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                  stroke="white" strokeWidth="2.5" strokeLinecap="round">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>

            <div className="login-footer">
              By continuing you agree to our{" "}
              <a>Terms of Use</a> &amp; <a>Privacy Policy</a>
            </div>
          </div>
          {toast && <Toast msg={toast.msg} sub={toast.sub} color={toast.color} onClose={() => setToast(null)} />}
        </div>
      </>
    );
  }

  /* ══════════════════════════════════════
     SCREEN 3 — ROLE SELECTION
  ══════════════════════════════════════ */
  if (appView === "roles") {
    const tiles = [
      { key: "student", emoji: "🎒", name: "Student",  sub: "Notes & homework",  glow: "rgba(108,71,255,0.25)" },
      { key: "teacher", emoji: "📖", name: "Teacher",  sub: "Manage classes",    glow: "rgba(244,63,94,0.25)"  },
      { key: "owner",   emoji: "🏫", name: "Owner",    sub: "Institute control", glow: "rgba(16,185,129,0.25)" },
      { key: "parent",  emoji: "👨‍👧", name: "Parent",   sub: "Track your child",  glow: "rgba(14,165,233,0.25)" },
    ];
    return (
      <>
        <style>{style}</style>
        <div className="shell">
          <div className="splash">
            <div className="splash-blob" style={{ width:260, height:260, background:T.violet,  top:-80,   right:-80,  animationDelay:"0s",   opacity:0.2  }} />
            <div className="splash-blob" style={{ width:180, height:180, background:T.rose,    bottom:60, left:-50,   animationDelay:"2.5s", opacity:0.18 }} />
            <div className="splash-blob" style={{ width:130, height:130, background:"#A855F7", top:"42%", left:"55%", animationDelay:"5s",   opacity:0.15 }} />

            <div className="splash-logo-wrap">
              <div className="splash-logo-bg">🎓</div>
            </div>
            <div className="splash-brand">
              <div className="splash-title">Nagana<em>verse</em></div>
              <div className="splash-tagline">Redefining Coaching Education</div>
            </div>

            <div style={{ height:32 }} />
            <div className="role-prompt">Who are you?</div>

            <div className="role-grid">
              {tiles.map((t, i) => (
                <div key={t.key} className="role-tile" style={{ animationDelay:`${0.1 + i * 0.07}s` }}
                  onClick={() => { setRole(t.key); setAppView("dashboard"); setTab("home"); }}>
                  <div className="role-tile-glow" style={{ background:`radial-gradient(circle at 50% 0%, ${t.glow}, transparent 70%)` }} />
                  <span className="role-emoji">{t.emoji}</span>
                  <div className="role-tile-name">{t.name}</div>
                  <div className="role-tile-sub">{t.sub}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </>
    );
  }

  /* ══════════════════════════════════════
     SCREEN 4 — DASHBOARD
  ══════════════════════════════════════ */
  const prof = roles[role];

  /* 4 tabs — Profile removed from nav, accessed via avatar */
  const navItems = [
    { id: "home",      label: "Home",                                    Icon: Home },
    { id: "classes",   label: role === "owner" ? "Students" : "Classes", Icon: role === "owner" ? Users : BookOpen },
    { id: "resources", label: "Resources",                               Icon: FolderOpen },
    { id: "analytics", label: "Analytics",                               Icon: BarChart2 },
  ];

  /* ── HAMBURGER BUTTON ── */
  const HamburgerBtn = () => (
    <div
      onClick={() => setDrawerOpen(true)}
      style={{
        width:38, height:38, borderRadius:12,
        background:T.surface, border:`1px solid ${T.border}`,
        display:"flex", alignItems:"center", justifyContent:"center",
        cursor:"pointer", flexShrink:0,
        transition:"transform 0.2s",
      }}>
      <Menu size={17} color={T.ink} />
    </div>
  );

  /* ── SIDE DRAWER ── */
  const SideDrawer = () => {
    const items = [
      { Icon: User,          bg:"#F3EEFF", color:T.violet,  label:"View Profile",  action:() => { setDrawerOpen(false); setSelectedStudent(null); setTab("profile"); } },
      { Icon: Moon,          bg:"#F0F9FF", color:T.sky,     label:`Dark Mode ${darkMode?"· ON":"· OFF"}`, action:() => setDarkMode(d => !d) },
      { Icon: Settings,      bg:"#FFFBEB", color:T.amber,   label:"Settings",      action:() => { setDrawerOpen(false); showToast("Settings", "Coming soon!", T.amber); } },
      { Icon: Info,          bg:"#ECFDF5", color:T.emerald, label:"About Us",      action:() => { setDrawerOpen(false); showToast("Naganaverse", "v2.0 · Built with ❤️", T.emerald); } },
    ];
    return (
      <>
        <div className="drawer-overlay" onClick={() => setDrawerOpen(false)} />
        <div className="side-drawer">
          {/* Drawer Header */}
          <div className="drawer-header">
            <div className="hero-orb" style={{ width:120, height:120, right:-30, top:-30, opacity:0.15 }} />
            <div style={{ width:52, height:52, borderRadius:16, background:`linear-gradient(135deg,${prof.color},${prof.color}99)`, display:"flex", alignItems:"center", justifyContent:"center", fontWeight:800, fontSize:16, color:"white", marginBottom:12, border:"2px solid rgba(255,255,255,0.15)" }}>
              {prof.init}
            </div>
            <div style={{ fontWeight:800, fontSize:16, color:"white", letterSpacing:-0.4 }}>{prof.name}</div>
            <div style={{ fontSize:11, color:"rgba(255,255,255,0.45)", marginTop:3 }}>{prof.sub}</div>
            <div style={{ display:"inline-flex", alignItems:"center", gap:5, background:"rgba(255,255,255,0.1)", padding:"4px 10px", borderRadius:20, marginTop:10, color:T.amber, fontSize:10, fontWeight:700 }}>
              <Star size={10} />{prof.badge}
            </div>
          </div>

          {/* Drawer Items */}
          <div style={{ flex:1, overflowY:"auto" }}>
            {items.map(({ Icon, bg, color, label, action }, i) => (
              <div key={i} className="drawer-item" onClick={action}>
                <div className="drawer-item-ico" style={{ background:bg }}><Icon size={17} color={color} /></div>
                <div className="drawer-item-lbl">{label}</div>
                <ChevronRight size={14} color={T.muted} />
              </div>
            ))}
          </div>

          {/* Logout */}
          <div className="drawer-footer">
            <div className="drawer-item" style={{ border:"none", borderRadius:14, background:"#FFF1F2" }}
              onClick={() => { setDrawerOpen(false); setRole(null); setAppView("splash"); setTab("home"); setAtt({}); setPhone(""); }}>
              <div className="drawer-item-ico" style={{ background:"#FFE4E6" }}><LogOut size={17} color={T.rose} /></div>
              <div className="drawer-item-lbl" style={{ color:T.rose }}>Logout</div>
            </div>
          </div>
        </div>
      </>
    );
  };

  /* ── STUDENT PROFILE DEEP-DIVE VIEW ── */
  const StudentProfileView = ({ student, onBack }) => (
    <>
      <div className="topbar anim-fadeup">
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div onClick={onBack} style={{ width:38, height:38, borderRadius:12, background:T.surface, border:`1px solid ${T.border}`, display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer" }}>
            <ArrowLeft size={16} color={T.ink} />
          </div>
          <div style={{ fontSize:18, fontWeight:800, color:T.ink, letterSpacing:-0.4 }}>Student Profile</div>
        </div>
      </div>

      {/* ID Card Hero */}
      <div style={{ margin:"16px 20px 0", background:`linear-gradient(145deg,${student.color},${student.color}bb)`, borderRadius:26, padding:"26px 22px", position:"relative", overflow:"hidden" }} className="anim-scale">
        <div className="hero-orb" style={{ width:180, height:180, right:-50, top:-50, opacity:0.14 }} />
        <div style={{ display:"flex", alignItems:"flex-start", gap:16 }}>
          {student.image
            ? <img src={student.image} alt={student.name} style={{ width:74, height:74, borderRadius:20, objectFit:"cover", border:"3px solid rgba(255,255,255,0.3)", flexShrink:0 }} />
            : <div style={{ width:74, height:74, borderRadius:20, background:"rgba(255,255,255,0.25)", display:"flex", alignItems:"center", justifyContent:"center", fontWeight:800, fontSize:26, color:"white", border:"3px solid rgba(255,255,255,0.3)", flexShrink:0 }}>{student.init}</div>
          }
          <div style={{ flex:1, minWidth:0 }}>
            <div style={{ fontWeight:800, fontSize:20, color:"white", letterSpacing:-0.5, lineHeight:1.1 }}>{student.name}</div>
            <div style={{ fontSize:12, color:"rgba(255,255,255,0.72)", marginTop:5, lineHeight:1.4 }}>{student.class} · {student.batch}</div>
            <div style={{ display:"flex", gap:8, marginTop:12, flexWrap:"wrap" }}>
              <div style={{ background:"rgba(255,255,255,0.2)", borderRadius:10, padding:"5px 12px", backdropFilter:"blur(8px)" }}>
                <div style={{ fontSize:8.5, color:"rgba(255,255,255,0.6)", fontWeight:700, letterSpacing:0.8, textTransform:"uppercase" }}>Roll No.</div>
                <div style={{ fontSize:15, color:"white", fontWeight:800, fontFamily:"Space Mono,monospace" }}>#{student.roll}</div>
              </div>
              <div style={{ background:"rgba(255,255,255,0.2)", borderRadius:10, padding:"5px 12px", backdropFilter:"blur(8px)" }}>
                <div style={{ fontSize:8.5, color:"rgba(255,255,255,0.6)", fontWeight:700, letterSpacing:0.8, textTransform:"uppercase" }}>Attendance</div>
                <div style={{ fontSize:15, color:"white", fontWeight:800, fontFamily:"Space Mono,monospace" }}>{student.att}%</div>
              </div>
            </div>
          </div>
        </div>
        <div style={{ marginTop:14 }}><FeePill fee={student.fee} /></div>
      </div>

      {/* Parent Contact Hub */}
      <div className="sec anim-fadeup" style={{ animationDelay:"0.1s" }}>
        <div className="sec-head"><div className="sec-title">Parent Contact Hub</div></div>
        <div style={{ background:"white", borderRadius:22, padding:"18px 18px 14px", boxShadow:"var(--shadow)", border:`1px solid ${T.border}` }}>

          {/* Father Row */}
          <div style={{ display:"flex", alignItems:"center", gap:12, paddingBottom:14, borderBottom:`1px solid ${T.border}`, marginBottom:14 }}>
            <div style={{ width:46, height:46, borderRadius:14, background:"#F3EEFF", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
              <User size={18} color={T.violet} />
            </div>
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ fontSize:9, color:T.muted, fontWeight:700, letterSpacing:1, textTransform:"uppercase", marginBottom:2 }}>Father</div>
              <div style={{ fontWeight:800, fontSize:13.5, color:T.ink, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{student.parents.father}</div>
            </div>
            <div style={{ display:"flex", gap:7 }}>
              <a href={`https://wa.me/91${student.parents.whatsapp}`} target="_blank" rel="noreferrer" className="sp-action-btn" style={{ background:"#ECFDF5" }}>
                <MessageSquare size={15} color={T.emerald} />
              </a>
              <a href={`tel:+91${student.parents.phone}`} className="sp-action-btn" style={{ background:"#F0F9FF" }}>
                <Phone size={15} color={T.sky} />
              </a>
              <a href={`mailto:${student.parents.email}`} className="sp-action-btn" style={{ background:"#F3EEFF" }}>
                <Mail size={15} color={T.violet} />
              </a>
            </div>
          </div>

          {/* Mother Row */}
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <div style={{ width:46, height:46, borderRadius:14, background:"#FFF1F2", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
              <User size={18} color={T.rose} />
            </div>
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ fontSize:9, color:T.muted, fontWeight:700, letterSpacing:1, textTransform:"uppercase", marginBottom:2 }}>Mother</div>
              <div style={{ fontWeight:800, fontSize:13.5, color:T.ink, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{student.parents.mother}</div>
            </div>
            <div style={{ display:"flex", gap:7 }}>
              <a href={`https://wa.me/91${student.parents.whatsapp}`} target="_blank" rel="noreferrer" className="sp-action-btn" style={{ background:"#ECFDF5" }}>
                <MessageSquare size={15} color={T.emerald} />
              </a>
              <a href={`tel:+91${student.parents.phone}`} className="sp-action-btn" style={{ background:"#F0F9FF" }}>
                <Phone size={15} color={T.sky} />
              </a>
              <a href={`mailto:${student.parents.email}`} className="sp-action-btn" style={{ background:"#F3EEFF" }}>
                <Mail size={15} color={T.violet} />
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="sec anim-fadeup" style={{ animationDelay:"0.18s", paddingBottom:8 }}>
        <div className="sec-head"><div className="sec-title">Quick Stats</div></div>
        <div style={{ background:"white", borderRadius:20, padding:"16px 18px", boxShadow:"var(--shadow)", border:`1px solid ${T.border}` }}>
          <div style={{ display:"flex", justifyContent:"space-between", marginBottom:8 }}>
            <span style={{ fontSize:13, fontWeight:700, color:T.ink }}>Attendance Rate</span>
            <span style={{ fontSize:13, fontWeight:800, color:student.att>80?T.emerald:student.att>65?T.amber:T.rose, fontFamily:"Space Mono,monospace" }}>{student.att}%</span>
          </div>
          <div className="pbar-wrap">
            <div className="pbar-fill" style={{ width:`${student.att}%`, background:student.att>80?T.emerald:student.att>65?T.amber:T.rose }} />
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10, marginTop:14 }}>
            {[
              { l:"Class",  v:student.class.replace("Class ","") + (student.class.includes("Class")?"th":"") },
              { l:"Batch",  v:student.batch.split(" ")[0] },
              { l:"Fee",    v:student.fee.charAt(0).toUpperCase()+student.fee.slice(1) },
            ].map((m,j) => (
              <div key={j} style={{ background:T.surface, borderRadius:12, padding:"9px 8px", textAlign:"center", border:`1px solid ${T.border}` }}>
                <div style={{ fontWeight:800, fontSize:12, color:T.ink }}>{m.v}</div>
                <div style={{ fontSize:9.5, color:T.muted, fontWeight:600, marginTop:2 }}>{m.l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );

  /* ─── OWNER HOME ─── */
  const OwnerHome = () => (
    <>
      <div className="topbar anim-fadeup">
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <HamburgerBtn />
          <div>
            <div style={{ fontSize:11, color:T.muted, fontWeight:600 }}>Good morning 👋</div>
            <div className="page-title">Dashboard</div>
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <div className="notif-dot"><Bell size={16} color={T.slate} /><div className="notif-badge" /></div>
          <div className="avatar-chip" style={{ background:`linear-gradient(135deg,${prof.color},${prof.color}99)` }} onClick={() => handleTabChange("profile")}>{prof.init}</div>
        </div>
      </div>

      <div className="hero anim-fadeup" style={{ background:`linear-gradient(145deg,${T.ink},${T.ink2},#2D1060)`, animationDelay:"0.06s" }}>
        <div className="hero-orb" style={{ width:160, height:160, right:-40, top:-40, opacity:0.12 }} />
        <div className="hero-orb" style={{ width:100, height:100, right:50, bottom:-30, opacity:0.08 }} />
        <div className="hero-chip"><Sparkles size={10} />Batch Insights</div>
        <div className="hero-h">Weekly Summary</div>
        <div className="hero-p">Strong performance across JEE & NEET batches this week</div>
        <div className="hero-stats">
          <div className="hero-stat"><div className="hero-stat-n">94%</div><div className="hero-stat-l">Avg Attend</div></div>
          <div className="hero-stat"><div className="hero-stat-n">6</div><div className="hero-stat-l">Batches</div></div>
          <div className="hero-stat"><div className="hero-stat-n">₹2.1L</div><div className="hero-stat-l">Pending</div></div>
        </div>
      </div>

      <div className="stat-grid anim-fadeup" style={{ animationDelay:"0.1s" }}>
        {[
          { n:"142", l:"Total Students",  Icon:Users,         grad:`linear-gradient(135deg,${T.violet},#A855F7)`, badge:"+12"   },
          { n:"18",  l:"Total Teachers",  Icon:GraduationCap, grad:`linear-gradient(135deg,${T.rose},#FB923C)`,   badge:"+2"    },
          { n:"87%", l:"Attendance Rate", Icon:CheckCircle,   grad:`linear-gradient(135deg,${T.emerald},${T.sky})`,badge:"↑3%" },
          { n:"14",  l:"Fees Due",        Icon:AlertCircle,   grad:`linear-gradient(135deg,${T.amber},#F97316)`,  badge:"₹2.1L" },
        ].map((s,i) => (
          <div key={i} className="stat-tile anim-scale" style={{ background:s.grad, animationDelay:`${0.13+i*0.06}s` }}>
            <div className="stat-tile-icon"><s.Icon size={17} color="white" /></div>
            <div className="stat-tile-badge">{s.badge}</div>
            <div className="stat-tile-n">{s.n}</div>
            <div className="stat-tile-l">{s.l}</div>
          </div>
        ))}
      </div>

      <div className="sec anim-fadeup" style={{ animationDelay:"0.18s" }}>
        <div className="sec-head"><div className="sec-title">Quick Actions</div></div>
      </div>
      <div className="actions-row" style={{ paddingBottom:4 }}>
        {[
          { l:"Add Student", Icon:Plus,          bg:`linear-gradient(135deg,${T.violet},#A855F7)` },
          { l:"Add Teacher", Icon:GraduationCap, bg:`linear-gradient(135deg,${T.rose},#FB923C)` },
          { l:"New Batch",   Icon:Layers,        bg:`linear-gradient(135deg,${T.emerald},${T.sky})` },
          { l:"Announce",    Icon:Bell,          bg:`linear-gradient(135deg,${T.amber},#F97316)` },
          { l:"Reports",     Icon:BarChart2,     bg:`linear-gradient(135deg,${T.ink},${T.ink3})` },
        ].map((a,i) => (
          <div key={i} className="action-pill anim-scale" style={{ animationDelay:`${0.2+i*0.05}s` }}
            onClick={() => showToast(a.l, "Feature coming soon!", T.violet)}>
            <div className="action-pip" style={{ background:a.bg }}><a.Icon size={22} color="white" /></div>
            <div className="action-lbl">{a.l}</div>
          </div>
        ))}
      </div>

      <div className="sec anim-fadeup" style={{ animationDelay:"0.26s" }}>
        <div className="sec-head">
          <div className="sec-title">Students</div>
          <div className="sec-link" onClick={() => handleTabChange("classes")}>View All</div>
        </div>
        {students.slice(0,3).map((s,i) => (
          <div key={s.id} className="card-row anim-slide" style={{ animationDelay:`${0.28+i*0.06}s` }}
            onClick={() => { setSelectedStudent(s); setTab("classes"); }}>
            {s.image
              ? <img src={s.image} alt={s.name} style={{ width:46, height:46, borderRadius:14, objectFit:"cover", flexShrink:0 }} />
              : <div className="avatar" style={{ width:46, height:46, background:s.color, fontSize:13 }}>{s.init}</div>
            }
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ fontWeight:700, fontSize:13.5, color:T.ink }}>{s.name}</div>
              <div style={{ fontSize:11, color:T.muted, marginTop:2 }}>{s.class} · {s.batch}</div>
              <div className="pbar-wrap">
                <div className="pbar-fill" style={{ width:`${s.att}%`, background:s.att>80?T.emerald:s.att>65?T.amber:T.rose }} />
              </div>
            </div>
            <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:5 }}>
              <FeePill fee={s.fee} />
              <span style={{ fontSize:11, color:T.muted, fontWeight:700, fontFamily:"Space Mono,monospace" }}>{s.att}%</span>
            </div>
          </div>
        ))}
      </div>
    </>
  );

  /* ─── TEACHER HOME ─── */
  const TeacherHome = () => (
    <>
      <div className="topbar anim-fadeup">
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <HamburgerBtn />
          <div>
            <div style={{ fontSize:11, color:T.muted, fontWeight:600 }}>Ready to teach? 📖</div>
            <div className="page-title">My Dashboard</div>
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <div className="notif-dot"><Bell size={16} color={T.slate} /><div className="notif-badge" /></div>
          <div className="avatar-chip" style={{ background:`linear-gradient(135deg,${T.teacherC},#FB923C)` }} onClick={() => handleTabChange("profile")}>{prof.init}</div>
        </div>
      </div>

      <div className="hero anim-fadeup" style={{ background:`linear-gradient(135deg,${T.rose},#9F1239)`, animationDelay:"0.06s" }}>
        <div className="hero-orb" style={{ width:140, height:140, right:-30, top:-30, opacity:0.12 }} />
        <div className="hero-chip"><Calendar size={10} />Today's Schedule</div>
        <div className="hero-h">4 Classes<br/>Today</div>
        <div className="hero-p">JEE Adv. + NEET batches</div>
        <div className="hero-stats">
          <div className="hero-stat"><div className="hero-stat-n">68</div><div className="hero-stat-l">Students</div></div>
          <div className="hero-stat"><div className="hero-stat-n">3</div><div className="hero-stat-l">HW Due</div></div>
        </div>
      </div>

      <div className="sec anim-fadeup" style={{ animationDelay:"0.1s" }}>
        <div className="sec-head"><div className="sec-title">Today's Classes</div></div>
        {todaysClasses.map((c,i) => (
          <div key={c.id} className="class-row anim-slide" style={{ animationDelay:`${0.12+i*0.06}s` }}>
            <div className="class-time-box">
              <div style={{ fontWeight:800, fontSize:15, color:T.ink, fontFamily:"Space Mono,monospace" }}>{c.time}</div>
              <div style={{ fontSize:9, color:T.muted, fontWeight:600 }}>{c.per}</div>
            </div>
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:700, fontSize:13.5, color:T.ink }}>{c.name}</div>
              <div style={{ fontSize:11, color:T.muted, marginTop:2 }}>{c.batch}</div>
            </div>
            <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:4 }}>
              <div style={{ width:8, height:8, borderRadius:"50%", background:c.status==="ongoing"?T.emerald:T.border }} />
              {c.status==="ongoing" && <span className="pill pill-green">Live</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="sec anim-fadeup" style={{ animationDelay:"0.22s" }}>
        <div className="sec-head"><div className="sec-title">Quick Actions</div></div>
      </div>
      <div className="actions-row" style={{ paddingBottom:4 }}>
        {[
          { l:"Attendance", Icon:CheckCircle, bg:`linear-gradient(135deg,${T.emerald},${T.sky})`, goTab:"classes"  },
          { l:"Homework",   Icon:BookMarked,  bg:`linear-gradient(135deg,${T.violet},#A855F7)`,  goTab:"resources" },
          { l:"Upload",     Icon:Upload,      bg:`linear-gradient(135deg,${T.amber},#F97316)`,   goTab:"resources" },
          { l:"Announce",   Icon:Bell,        bg:`linear-gradient(135deg,${T.ink},${T.ink3})`,   goTab:null        },
        ].map((a,i) => (
          <div key={i} className="action-pill anim-scale" style={{ animationDelay:`${0.24+i*0.05}s` }}
            onClick={() => a.goTab ? handleTabChange(a.goTab) : showToast("Announcement Sent!", "All students notified", T.violet)}>
            <div className="action-pip" style={{ background:a.bg }}><a.Icon size={22} color="white" /></div>
            <div className="action-lbl">{a.l}</div>
          </div>
        ))}
      </div>
    </>
  );

  /* ─── STUDENT HOME ─── */
  const StudentHome = () => (
    <>
      <div className="topbar anim-fadeup">
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <HamburgerBtn />
          <div>
            <div style={{ fontSize:11, color:T.muted, fontWeight:600 }}>Keep going! 🔥</div>
            <div className="page-title">Hi, Aryan</div>
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <div className="notif-dot"><Bell size={16} color={T.slate} /><div className="notif-badge" /></div>
          <div className="avatar-chip" style={{ background:`linear-gradient(135deg,${T.studentC},#A855F7)` }} onClick={() => handleTabChange("profile")}>{prof.init}</div>
        </div>
      </div>

      <div className="hero anim-fadeup" style={{ background:`linear-gradient(135deg,${T.violet},#7C3AED)`, animationDelay:"0.06s" }}>
        <div className="hero-orb" style={{ width:150, height:150, right:-30, top:-30, opacity:0.12 }} />
        <div className="hero-chip"><Target size={10} />JEE Countdown</div>
        <div className="hero-h">127 Days<br/>to JEE Mains!</div>
        <div className="hero-p">Stay consistent — you're on track 🎯</div>
        <div className="hero-stats">
          <div className="hero-stat"><div className="hero-stat-n">88%</div><div className="hero-stat-l">Attendance</div></div>
          <div className="hero-stat"><div className="hero-stat-n">3</div><div className="hero-stat-l">HW Due</div></div>
          <div className="hero-stat"><div className="hero-stat-n">82%</div><div className="hero-stat-l">Avg Score</div></div>
        </div>
      </div>

      <div className="sec anim-fadeup" style={{ animationDelay:"0.1s" }}>
        <div className="sec-head">
          <div className="sec-title">Today's Homework</div>
          <div className="sec-link">See All</div>
        </div>
        {homeworkList.map((h,i) => (
          <div key={h.id} className="hw-card anim-slide" style={{ borderLeftColor:h.color, animationDelay:`${0.12+i*0.07}s` }}>
            <div style={{ fontSize:10, fontWeight:800, color:h.color, letterSpacing:1, textTransform:"uppercase", marginBottom:5 }}>{h.subject}</div>
            <div style={{ fontWeight:700, fontSize:14, color:T.ink }}>{h.topic}</div>
            <div style={{ display:"flex", alignItems:"center", gap:6, marginTop:9 }}>
              <Clock size={11} color={T.muted} />
              <span style={{ fontSize:11, color:T.muted, fontWeight:500 }}>Due: {h.due}</span>
            </div>
            <button className="btn-primary" style={{ marginTop:11, padding:"9px", borderRadius:12, fontSize:12 }}>
              View Homework
            </button>
          </div>
        ))}
      </div>

      <div className="sec anim-fadeup" style={{ animationDelay:"0.2s" }}>
        <div className="sec-head"><div className="sec-title">Announcements</div><div className="sec-link">All</div></div>
        {announcements.slice(0,2).map((a,i) => (
          <div key={a.id} className="ann-card anim-fadeup" style={{ background:a.grad, animationDelay:`${0.22+i*0.08}s` }}>
            <div style={{ width:38, height:38, background:"rgba(255,255,255,0.18)", borderRadius:13, display:"flex", alignItems:"center", justifyContent:"center", fontSize:18, marginBottom:11 }}>{a.icon}</div>
            <div style={{ fontWeight:800, fontSize:15.5, color:"white", marginBottom:5, letterSpacing:-0.3 }}>{a.title}</div>
            <div style={{ fontSize:12, color:"rgba(255,255,255,0.72)", lineHeight:1.5 }}>{a.body}</div>
            <div style={{ display:"flex", alignItems:"center", gap:5, marginTop:10, fontSize:10, color:"rgba(255,255,255,0.5)" }}>
              <Clock size={10} />{a.time}
            </div>
          </div>
        ))}
      </div>
    </>
  );

  /* ─── PARENT HOME ─── */
  const ParentHome = () => (
    <>
      <div className="topbar anim-fadeup">
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <HamburgerBtn />
          <div>
            <div style={{ fontSize:11, color:T.muted, fontWeight:600 }}>Welcome back 👋</div>
            <div className="page-title">My Child</div>
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <div className="notif-dot"><Bell size={16} color={T.slate} /><div className="notif-badge" /></div>
          <div className="avatar-chip" style={{ background:`linear-gradient(135deg,${T.parentC},#6366F1)` }} onClick={() => handleTabChange("profile")}>{prof.init}</div>
        </div>
      </div>

      <div className="child-card anim-fadeup" style={{ animationDelay:"0.06s" }}>
        <div className="hero-orb" style={{ width:140, height:140, right:-30, top:-30, opacity:0.1 }} />
        <div style={{ display:"flex", alignItems:"center", gap:14, marginBottom:18 }}>
          <div style={{ width:56, height:56, borderRadius:18, background:T.studentC, display:"flex", alignItems:"center", justifyContent:"center", fontWeight:800, fontSize:18, color:"white", border:"2px solid rgba(255,255,255,0.15)" }}>AS</div>
          <div>
            <div style={{ fontWeight:800, fontSize:17, color:"white", letterSpacing:-0.4 }}>Aryan Sharma</div>
            <div style={{ fontSize:11, color:"rgba(255,255,255,0.45)", marginTop:3 }}>Class 11 · JEE Advanced Batch</div>
            <span className="pill pill-violet" style={{ marginTop:6, display:"inline-flex" }}>Roll #001</span>
          </div>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10 }}>
          {[
            { n:"88%", l:"Attendance", color:T.emerald },
            { n:"2/3",  l:"HW Done",   color:T.violet },
            { n:"82%", l:"Avg Score",  color:T.amber },
          ].map((s,i) => (
            <div key={i} style={{ background:"rgba(255,255,255,0.12)", borderRadius:14, padding:"10px 8px", textAlign:"center", backdropFilter:"blur(8px)" }}>
              <div style={{ fontWeight:800, fontSize:18, color:"white", fontFamily:"Space Mono,monospace" }}>{s.n}</div>
              <div style={{ fontSize:9, color:"rgba(255,255,255,0.5)", fontWeight:600, marginTop:3 }}>{s.l}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="sec anim-fadeup" style={{ animationDelay:"0.14s" }}>
        <div className="sec-head"><div className="sec-title">Subject Attendance</div></div>
        {parentSubjectAtt.map((s,i) => (
          <div key={s.subj} className="subject-att-row anim-slide" style={{ animationDelay:`${0.16+i*0.06}s` }}>
            <div style={{ width:40, height:40, borderRadius:13, background:s.bg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:18 }}>
              {["⚡","🧪","📐","🧬"][i]}
            </div>
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:700, fontSize:13, color:T.ink }}>{s.subj}</div>
              <div className="pbar-wrap"><div className="pbar-fill" style={{ width:`${s.pct}%`, background:s.color }} /></div>
            </div>
            <div style={{ fontWeight:800, fontSize:14, color:s.color, fontFamily:"Space Mono,monospace" }}>{s.pct}%</div>
          </div>
        ))}
      </div>
    </>
  );

  const renderHome = () => {
    switch(role) {
      case "owner":   return <OwnerHome />;
      case "teacher": return <TeacherHome />;
      case "student": return <StudentHome />;
      case "parent":  return <ParentHome />;
      default:        return <OwnerHome />;
    }
  };

  /* ─── OWNER STUDENTS TAB (Overhaul) ─── */
  const OwnerStudents = () => {
    const [groupBy, setGroupBy]   = useState("class");
    const [search, setSearch]     = useState("");

    const isSearching = search.trim().length > 0;

    const filtered = students.filter(s =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.class.toLowerCase().includes(search.toLowerCase()) ||
      s.batch.toLowerCase().includes(search.toLowerCase()) ||
      s.roll.includes(search)
    );

    const byClass = classesList.reduce((acc, cls) => {
      const list = students.filter(s => s.class === cls);
      if (list.length) acc[cls] = list;
      return acc;
    }, {});

    const byBatch = batchesList.reduce((acc, bat) => {
      const list = students.filter(s => s.batch === bat);
      if (list.length) acc[bat] = list;
      return acc;
    }, {});

    const groups = groupBy === "class" ? byClass : byBatch;

    const StudentCard = ({ s, i }) => (
      <div key={s.id} className="card anim-slide"
        style={{ animationDelay:`${0.1+i*0.06}s`, padding:"14px 16px" }}
        onClick={() => setSelectedStudent(s)}>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          {s.image
            ? <img src={s.image} alt={s.name} style={{ width:48, height:48, borderRadius:14, objectFit:"cover", flexShrink:0 }} />
            : <div className="avatar" style={{ width:48, height:48, background:s.color }}>{s.init}</div>
          }
          <div style={{ flex:1, minWidth:0 }}>
            <div style={{ fontWeight:800, fontSize:14, color:T.ink }}>{s.name}</div>
            {isSearching ? (
              <div style={{ fontSize:11, color:T.muted, marginTop:2 }}>{s.class} · <span style={{ color:T.violet, fontWeight:700 }}>Roll #{s.roll}</span></div>
            ) : (
              <div style={{ fontSize:11, color:T.muted, marginTop:2 }}>{s.batch}</div>
            )}
            {isSearching && (
              <div style={{ fontSize:10, color:T.slate, marginTop:1 }}>{s.batch}</div>
            )}
          </div>
          <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:5 }}>
            <FeePill fee={s.fee} />
            <span style={{ fontSize:11, color:T.muted, fontWeight:700, fontFamily:"Space Mono,monospace" }}>{s.att}%</span>
          </div>
        </div>
      </div>
    );

    return (
      <>
        <div className="topbar anim-fadeup">
          <div className="page-title">Students</div>
          <div style={{ display:"flex", gap:8 }}>
            <div className="notif-dot" onClick={() => showToast("Add Student", "Opening form…", T.violet)}>
              <Plus size={15} color={T.violet} />
            </div>
          </div>
        </div>

        {/* Omni-Search */}
        <div style={{ padding:"14px 20px 0" }}>
          <div style={{ position:"relative" }}>
            <Search size={15} color={T.muted} style={{ position:"absolute", left:14, top:"50%", transform:"translateY(-50%)", pointerEvents:"none" }} />
            <input
              className="custom-input"
              placeholder="Search by name, class, roll…"
              style={{ paddingLeft:42, marginBottom:0 }}
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {isSearching && (
              <div onClick={() => setSearch("")} style={{ position:"absolute", right:14, top:"50%", transform:"translateY(-50%)", cursor:"pointer" }}>
                <X size={14} color={T.muted} />
              </div>
            )}
          </div>
        </div>

        {/* Controls row — hidden during search */}
        {!isSearching && (
          <div style={{ padding:"12px 20px 0", display:"flex", alignItems:"center", justifyContent:"space-between", gap:10 }}>
            <div className="group-toggle-wrap">
              {["class","batch"].map(g => (
                <button key={g} className="group-toggle-btn"
                  onClick={() => setGroupBy(g)}
                  style={{
                    background: groupBy===g ? T.violet : "transparent",
                    color: groupBy===g ? "white" : T.muted,
                    boxShadow: groupBy===g ? "0 3px 10px rgba(108,71,255,0.3)" : "none",
                  }}>
                  By {g.charAt(0).toUpperCase() + g.slice(1)}
                </button>
              ))}
            </div>
            <button
              onClick={() => showToast("Create Batch", "Coming soon!", T.emerald)}
              style={{
                background:`linear-gradient(135deg,${T.emerald},#22D3EE)`,
                color:"white", border:"none", borderRadius:12,
                padding:"9px 14px", fontSize:11, fontWeight:700,
                cursor:"pointer", display:"flex", alignItems:"center", gap:5,
                fontFamily:"'Sora', sans-serif",
                boxShadow:"0 4px 14px rgba(16,185,129,0.3)",
                flexShrink:0,
              }}>
              <Plus size={13} /> Create Batch
            </button>
          </div>
        )}

        <div className="sec anim-fadeup" style={{ animationDelay:"0.08s" }}>
          {isSearching ? (
            <>
              <div className="sec-head">
                <div className="sec-title">
                  Search Results <span style={{ color:T.muted, fontSize:12, fontWeight:500 }}>({filtered.length})</span>
                </div>
              </div>
              {filtered.length === 0 ? (
                <div className="empty">
                  <div className="empty-ico"><Search size={28} color={T.muted} /></div>
                  <div style={{ fontWeight:800, fontSize:16, color:T.ink, marginBottom:6 }}>No matches found</div>
                  <div style={{ fontSize:13, color:T.muted }}>Try a different name, class, or roll number.</div>
                </div>
              ) : (
                filtered.map((s, i) => <StudentCard key={s.id} s={s} i={i} />)
              )}
            </>
          ) : (
            Object.entries(groups).map(([groupName, list]) => (
              <div key={groupName} style={{ marginBottom:22 }}>
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
                  <div style={{ fontWeight:800, fontSize:14, color:T.ink, letterSpacing:-0.3 }}>{groupName}</div>
                  <div style={{ background:`${T.violet}18`, color:T.violet, borderRadius:20, padding:"2px 9px", fontSize:10, fontWeight:800 }}>{list.length}</div>
                </div>
                {list.map((s, i) => <StudentCard key={s.id} s={s} i={i} />)}
              </div>
            ))
          )}
        </div>
      </>
    );
  };

  /* ─── TEACHER / STUDENT CLASSES TAB ─── */
  const renderClasses = () => {
    if (role === "owner") return <OwnerStudents />;

    /* Teacher attendance view */
    return (
      <>
        <div className="topbar anim-fadeup"><div className="page-title">{role==="student"?"My Classes":"Take Attendance"}</div></div>
        <div className="sec anim-fadeup" style={{ animationDelay:"0.06s" }}>
          <div className="sec-head"><div className="sec-title">{role==="student"?"Today's Schedule":"Today – JEE Adv. A"}</div></div>
          {role === "student"
            ? todaysClasses.map((c,i) => (
                <div key={c.id} className="class-row anim-slide" style={{ animationDelay:`${0.08+i*0.06}s` }}>
                  <div className="class-time-box">
                    <div style={{ fontWeight:800, fontSize:15, color:T.ink, fontFamily:"Space Mono,monospace" }}>{c.time}</div>
                    <div style={{ fontSize:9, color:T.muted, fontWeight:600 }}>{c.per}</div>
                  </div>
                  <div style={{ flex:1 }}>
                    <div style={{ fontWeight:700, fontSize:13.5, color:T.ink }}>{c.name}</div>
                    <div style={{ fontSize:11, color:T.muted, marginTop:2 }}>{c.batch}</div>
                  </div>
                  <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:4 }}>
                    <div style={{ width:8, height:8, borderRadius:"50%", background:c.status==="ongoing"?T.emerald:T.border }} />
                    {c.status==="ongoing" && <span className="pill pill-green">Live</span>}
                  </div>
                </div>
              ))
            : students.map((s,i) => (
                <div key={s.id} className="att-row anim-slide" style={{ animationDelay:`${0.08+i*0.06}s` }}>
                  {s.image
                    ? <img src={s.image} alt={s.name} style={{ width:40, height:40, borderRadius:12, objectFit:"cover" }} />
                    : <div className="avatar" style={{ width:40, height:40, background:s.color, fontSize:12 }}>{s.init}</div>
                  }
                  <div style={{ flex:1, minWidth:0 }}>
                    <div style={{ fontWeight:700, fontSize:13, color:T.ink }}>{s.name}</div>
                    <div style={{ fontSize:10, color:T.muted }}>{s.batch}</div>
                  </div>
                  <div style={{ display:"flex", gap:6 }}>
                    <button className={`att-btn att-p ${att[s.id]==="P"?"on":""}`} onClick={() => toggleAtt(s.id,"P")}>P</button>
                    <button className={`att-btn att-a ${att[s.id]==="A"?"on":""}`} onClick={() => toggleAtt(s.id,"A")}>A</button>
                  </div>
                </div>
              ))
          }
          {role === "teacher" && (
            <button className="btn-accent" style={{ marginTop:14 }}
              onClick={() => showToast("Attendance Saved! ✅", "Marked for JEE Adv. Batch A", T.emerald)}>
              <Check size={16} /> Save Attendance
            </button>
          )}
        </div>
      </>
    );
  };

  /* ─── RESOURCES TAB ─── */
  const renderResources = () => {
    if (role === "owner" || role === "teacher") return (
      <>
        <div className="topbar anim-fadeup"><div className="page-title">Resources</div></div>
        <div className="sec anim-fadeup" style={{ animationDelay:"0.06s" }}>
          <div className="sec-head"><div className="sec-title">Generate Homework</div></div>
          <div className="field-label">Batch</div>
          <select className="custom-select" value={hwBatch} onChange={e => setHwBatch(e.target.value)}>
            {batchesList.map(b => <option key={b}>{b}</option>)}
          </select>
          <div className="field-label">Subject</div>
          <select className="custom-select" value={hwSubj} onChange={e => { setHwSubj(e.target.value); setHwPreview(false); }}>
            {["Physics","Chemistry","Math"].map(s => <option key={s}>{s}</option>)}
          </select>
          <div className="field-label">Chapter</div>
          <select className="custom-select">
            <option>Optics & Wave Optics</option>
            <option>Kinematics</option>
            <option>Thermodynamics</option>
          </select>
          <button className="btn-accent" onClick={() => setHwPreview(true)}>
            <Sparkles size={16} /> Generate with AI
          </button>
          {hwPreview && (
            <div className="hw-preview">
              <div style={{ fontWeight:800, fontSize:13, color:T.violet, marginBottom:10 }}>📋 Generated – {hwSubj}</div>
              {(hwQs[hwSubj] || hwQs.Physics).map((q,i) => (
                <div key={i} className="hw-q">Q{i+1}. {q}</div>
              ))}
              <button className="btn-primary" style={{ marginTop:12 }}
                onClick={() => { setHwPreview(false); showToast("Homework Sent! 📚", `Sent to ${hwBatch}`, T.amber); }}>
                <Send size={15} /> Send to Students
              </button>
            </div>
          )}
        </div>

        <div style={{ fontWeight:800, fontSize:15, color:T.ink, marginBottom:14, padding:"20px 20px 0" }}>📁 Upload Notes</div>
        <div style={{ padding:"0 20px" }}>
          <div className={`upload-zone ${dragging?"drag":""}`}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); setUploaded(true); showToast("Uploaded! 🎉","File added to library",T.emerald); setTimeout(()=>setUploaded(false),3000); }}
            onClick={() => { setUploaded(true); showToast("Uploaded! 🎉","File added to library",T.emerald); setTimeout(()=>setUploaded(false),3000); }}>
            {uploaded
              ? <><div style={{ fontSize:40, marginBottom:10 }}>🎉</div><div style={{ fontWeight:800, fontSize:16, color:T.emerald }}>Upload Successful!</div></>
              : <>
                  <div className="upload-pip"><Upload size={26} color="white" /></div>
                  <div style={{ fontWeight:800, fontSize:16, color:T.ink, marginBottom:5 }}>Drag & Drop Files</div>
                  <div style={{ fontSize:12, color:T.muted }}>or tap to browse from device</div>
                  <div style={{ fontSize:10, color:T.muted, marginTop:8, fontWeight:600 }}>PDF · DOCX · MP4 · JPG · PNG</div>
                </>
            }
          </div>
        </div>
      </>
    );

    const filtered2 = activeSub === "All" ? files : files.filter(f => f.subject === activeSub);
    return (
      <>
        <div className="topbar anim-fadeup"><div className="page-title">Notes Library</div></div>
        <div style={{ paddingTop:14 }}>
          <div className="chip-row">
            {subjects.map(s => (
              <div key={s.name} className={`chip ${activeSub===s.name?"on":"off"}`}
                style={activeSub===s.name ? { background:`linear-gradient(135deg,${s.color},${s.color}cc)` } : {}}
                onClick={() => setActiveSub(s.name)}>
                {s.icon} {s.name}
              </div>
            ))}
          </div>
        </div>
        <div className="sec anim-fadeup" style={{ animationDelay:"0.1s" }}>
          {filtered2.length === 0
            ? <div className="empty">
                <div className="empty-ico"><FolderOpen size={32} color={T.muted} /></div>
                <div style={{ fontWeight:800, fontSize:17, color:T.ink, marginBottom:8 }}>No Files Yet</div>
                <div style={{ fontSize:13, color:T.muted }}>No notes uploaded for this subject.</div>
              </div>
            : filtered2.map((f,i) => (
              <div key={f.id} className="file-row anim-slide" style={{ animationDelay:`${0.12+i*0.07}s` }}>
                <div className="file-ico" style={{ background:f.bg }}><span style={{ color:f.color }}><FileIco type={f.type} /></span></div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ fontWeight:700, fontSize:13, color:T.ink }}>{f.name}</div>
                  <div style={{ fontSize:10.5, color:T.muted, marginTop:3 }}>{f.type.toUpperCase()} · {f.size} · {f.date}</div>
                </div>
                <Download size={17} color={T.muted} />
              </div>
            ))}
        </div>
      </>
    );
  };

  /* ─── ANALYTICS TAB ─── */
  const renderAnalytics = () => (
    <>
      <div className="topbar anim-fadeup"><div className="page-title">Analytics</div></div>
      <div className="hero anim-fadeup" style={{ background:`linear-gradient(135deg,${T.ink},${T.ink3})`, animationDelay:"0.06s" }}>
        <div className="hero-chip"><Activity size={10} />Performance</div>
        <div className="hero-h">{role==="student"?"Your Progress":"Institute Overview"}</div>
        <div className="hero-p">March 2026 · Weekly Report</div>
      </div>

      <div style={{ padding:"20px 20px 0" }}>
        <div className="sec-title" style={{ marginBottom:14 }}>Key Metrics</div>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10 }}>
          {[
            { l:"Attendance", v:88, color:T.emerald },
            { l:"HW Done",    v:72, color:T.violet },
            { l:"Avg Score",  v:81, color:T.rose },
          ].map((p,i) => (
            <div key={i} className="anim-scale" style={{ background:"white", borderRadius:20, padding:"16px 10px", textAlign:"center", boxShadow:"var(--shadow)", border:`1px solid ${T.border}`, animationDelay:`${0.12+i*0.08}s` }}>
              <div className="ring-wrap">
                <Ring v={p.v} color={p.color} size={64} />
                <div className="ring-val" style={{ fontSize:14, color:p.color }}>{p.v}%</div>
              </div>
              <div style={{ fontSize:10, fontWeight:700, color:T.muted, marginTop:8 }}>{p.l}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="sec anim-fadeup" style={{ animationDelay:"0.22s" }}>
        <div className="sec-head"><div className="sec-title">Subject Breakdown</div></div>
        {subjects.slice(1).map((s,i) => (
          <div key={s.name} className="subject-att-row anim-slide" style={{ animationDelay:`${0.24+i*0.06}s` }}>
            <div style={{ width:42, height:42, borderRadius:13, background:s.bg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:20 }}>{s.icon}</div>
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:700, fontSize:13.5, color:T.ink }}>{s.name}</div>
              <div className="pbar-wrap">
                <div className="pbar-fill" style={{ width:`${[78,65,90,55,82][i]}%`, background:s.color }} />
              </div>
            </div>
            <div style={{ fontWeight:800, fontSize:14, color:s.color, fontFamily:"Space Mono,monospace" }}>{[78,65,90,55,82][i]}%</div>
          </div>
        ))}
      </div>
    </>
  );

  /* ─── PROFILE TAB ─── */
  const renderProfile = () => (
    <>
      <div className="topbar anim-fadeup">
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div onClick={() => handleTabChange("home")} style={{ width:38, height:38, borderRadius:12, background:T.surface, border:`1px solid ${T.border}`, display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer" }}>
            <ArrowLeft size={16} color={T.ink} />
          </div>
          <div className="page-title" style={{ fontSize:18 }}>My Profile</div>
        </div>
      </div>
      <div className="profile-hero-bg" style={{ marginTop:12 }}>
        <div className="hero-orb" style={{ width:180, height:180, right:-60, top:-60, opacity:0.1 }} />
        <div className="profile-av" style={{ background:`linear-gradient(135deg,${prof.color},${prof.color}99)` }}>{prof.init}</div>
        <div className="profile-name-text">{prof.name}</div>
        <div className="profile-role-text">{prof.sub}</div>
        <div className="profile-badge-wrap"><Star size={12} /> {prof.badge}</div>
      </div>

      <div style={{ background:"white" }}>
        {[
          { Icon:User,          bg:"#F3EEFF", color:T.violet,  l:"Edit Profile" },
          { Icon:Bell,          bg:"#FFF1F2", color:T.rose,    l:"Notifications" },
          { Icon:BookOpen,      bg:"#ECFDF5", color:T.emerald, l:role==="student"?"My Subjects":"My Classes" },
          { Icon:Award,         bg:"#FFFBEB", color:T.amber,   l:"Achievements" },
          { Icon:Target,        bg:"#F0F9FF", color:T.sky,     l:"Goals & Progress" },
          { Icon:MessageSquare, bg:"#F3EEFF", color:T.violet,  l:"Help & Support" },
        ].map((m,i) => (
          <div key={i} className="menu-row" onClick={() => showToast(m.l, "Coming soon!", T.violet)}>
            <div className="menu-ico" style={{ background:m.bg }}><m.Icon size={17} color={m.color} /></div>
            <div className="menu-lbl">{m.l}</div>
            <ChevronRight size={15} color={T.muted} />
          </div>
        ))}
        <div className="menu-row" style={{ borderBottom:"none" }}
          onClick={() => { setRole(null); setAppView("splash"); setTab("home"); setAtt({}); setPhone(""); }}>
          <div className="menu-ico" style={{ background:"#FFF1F2" }}><LogOut size={17} color={T.rose} /></div>
          <div className="menu-lbl" style={{ color:T.rose }}>Switch Role / Logout</div>
          <ChevronRight size={15} color={T.rose} />
        </div>
      </div>
    </>
  );

  const renderContent = () => {
    if (selectedStudent) {
      return <StudentProfileView student={selectedStudent} onBack={() => setSelectedStudent(null)} />;
    }
    switch(tab) {
      case "home":      return renderHome();
      case "classes":   return renderClasses();
      case "resources": return renderResources();
      case "analytics": return renderAnalytics();
      case "profile":   return renderProfile();
      default:          return renderHome();
    }
  };

  return (
    <>
      <style>{style}</style>
      <div className="shell">
        <div className="scroll-area">{renderContent()}</div>
        {!selectedStudent && tab !== "profile" && (
          <nav className="bottom-nav">
            {navItems.map(({ id, label, Icon }) => (
              <div key={id} className={`nav-btn ${tab===id?"active":""}`} onClick={() => handleTabChange(id)}>
                <div className="nav-pip"><Icon size={17} /></div>
                <span className="nav-lbl">{label}</span>
              </div>
            ))}
          </nav>
        )}
        {drawerOpen && <SideDrawer />}
        {toast && <Toast msg={toast.msg} sub={toast.sub} color={toast.color} onClose={() => setToast(null)} />}
      </div>
    </>
  );
}
