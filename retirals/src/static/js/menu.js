document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('menu-toggle');
    const menu = document.getElementById('flyout-menu');
    if (!toggle || !menu) return;

    function openMenu() {
        const rect = toggle.getBoundingClientRect();
        const menuWidth = menu.offsetWidth || 192;
        menu.style.top = (rect.bottom + 8) + 'px';
        menu.style.right = 'auto';
        menu.style.left = 'auto';

        const fitsOnRight = rect.left + menuWidth <= window.innerWidth - 8;
        const fitsOnLeft = rect.right - menuWidth >= 8;

        if (fitsOnRight) {
            menu.style.left = rect.left + 'px';
        } else if (fitsOnLeft) {
            menu.style.left = Math.max(8, rect.right - menuWidth) + 'px';
        } else {
            menu.style.left = '8px';
            menu.style.right = '8px';
            menu.style.width = 'auto';
        }

        menu.classList.remove('hidden');
        toggle.setAttribute('aria-expanded', 'true');
        toggle.setAttribute('aria-label', 'Close menu');
    }

    function closeMenu() {
        menu.classList.add('hidden');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-label', 'Open menu');
    }

    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = !menu.classList.contains('hidden');
        if (isOpen) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    menu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            closeMenu();
        });
    });

    document.addEventListener('click', (e) => {
        if (!menu.contains(e.target) && e.target !== toggle) {
            closeMenu();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeMenu();
        }
    });

    window.addEventListener('resize', () => {
        if (!menu.classList.contains('hidden')) {
            closeMenu();
        }
    });

    updateAiInsightButtonState();
});
