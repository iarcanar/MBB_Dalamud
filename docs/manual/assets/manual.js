// MBB Manual — Shared scripts
// (1) Sidebar mobile toggle
// (2) Right TOC scroll-spy
// (3) Code block copy buttons
// (4) Section anchor links

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        initHamburger();
        initCopyButtons();
        initAnchorLinks();
        initTocScrollSpy();
        initDiagramToggles();
    });

    /* ── (5) Diagram ↔ Real UI toggle ── */
    function initDiagramToggles() {
        document.querySelectorAll('.diagram-toggleable').forEach(diagram => {
            const tabs = diagram.querySelectorAll('.diagram-tab');
            const views = diagram.querySelectorAll('.diagram-view');
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const target = tab.dataset.view;
                    tabs.forEach(t => t.classList.toggle('active', t.dataset.view === target));
                    views.forEach(v => {
                        v.classList.toggle('active', v.dataset.view === target);
                    });
                });
            });
        });
    }

    /* ── (1) Hamburger ── */
    function initHamburger() {
        const burger = document.querySelector('.hamburger');
        const sidebar = document.querySelector('.manual-sidebar');
        if (!burger || !sidebar) return;
        burger.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
        document.addEventListener('click', (e) => {
            if (window.innerWidth > 760) return;
            if (sidebar.contains(e.target) || burger.contains(e.target)) return;
            sidebar.classList.remove('open');
        });
    }

    /* ── (2) TOC scroll-spy ── */
    function initTocScrollSpy() {
        const toc = document.querySelector('.manual-toc');
        if (!toc) return;
        const links = toc.querySelectorAll('a[href^="#"]');
        if (!links.length) return;

        const map = new Map();
        links.forEach(a => {
            const id = a.getAttribute('href').slice(1);
            const target = document.getElementById(id);
            if (target) map.set(target, a);
        });

        const observer = new IntersectionObserver((entries) => {
            // pick the entry highest on screen (smallest y) that's intersecting
            let best = null;
            for (const entry of entries) {
                if (entry.isIntersecting) {
                    if (!best || entry.boundingClientRect.top < best.boundingClientRect.top) {
                        best = entry;
                    }
                }
            }
            if (best) {
                links.forEach(a => a.classList.remove('active'));
                const a = map.get(best.target);
                if (a) a.classList.add('active');
            }
        }, {
            rootMargin: '-80px 0px -70% 0px',
            threshold: 0
        });

        map.forEach((_, el) => observer.observe(el));
    }

    /* ── (3) Copy buttons ── */
    function initCopyButtons() {
        document.querySelectorAll('pre').forEach(pre => {
            if (pre.querySelector('.copy-btn')) return;
            const btn = document.createElement('button');
            btn.className = 'copy-btn';
            btn.textContent = 'Copy';
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const code = pre.querySelector('code') || pre;
                const text = code.innerText;
                try {
                    await navigator.clipboard.writeText(text);
                    btn.textContent = 'Copied!';
                    btn.classList.add('copied');
                    setTimeout(() => {
                        btn.textContent = 'Copy';
                        btn.classList.remove('copied');
                    }, 1600);
                } catch (err) {
                    btn.textContent = 'Failed';
                    setTimeout(() => { btn.textContent = 'Copy'; }, 1600);
                }
            });
            pre.appendChild(btn);
        });
    }

    /* ── (4) Anchor links on headings ── */
    function initAnchorLinks() {
        document.querySelectorAll('h2[id], h3[id]').forEach(h => {
            if (h.querySelector('.section-anchor')) return;
            const id = h.id;
            const a = document.createElement('a');
            a.className = 'section-anchor';
            a.href = `#${id}`;
            a.textContent = '#';
            a.setAttribute('aria-label', 'Link to this section');
            h.appendChild(a);
        });
    }
})();
