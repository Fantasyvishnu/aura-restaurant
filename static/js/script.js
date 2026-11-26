/**
 * AURA - MAIN JAVASCRIPT
 * Features:
 * - Navbar scroll state
 * - Animated number counters
 * - Menu / gallery category filter
 * - Reservation widget (time slots, guest counter, date limits)
 * - Gallery lightbox (mouse + keyboard)
 * - Live "Open / Closed" badge using per-day opening hours
 * - Back to top button
 *
 * (The old "scroll reveal" code was removed: the templates use AOS for animations.)
 */

/* ------------------------------------------------------------------
   RESTAURANT SETTINGS - keep in sync with OPENING_HOURS in forms.py
   and the "Service Hours" text in base.html
   ------------------------------------------------------------------ */
const RESTAURANT_TIMEZONE = 'Asia/Kolkata';   // Tamil Nadu (India Standard Time)
const OPENING_SCHEDULE = {
    // day: [openHour, openMinute, closeHour, closeMinute]   (24-hour clock)
    // AURA is open every day, 12:00 PM to 11:00 PM
    Mon: [12, 0, 23, 0],
    Tue: [12, 0, 23, 0],
    Wed: [12, 0, 23, 0],
    Thu: [12, 0, 23, 0],
    Fri: [12, 0, 23, 0],
    Sat: [12, 0, 23, 0],
    Sun: [12, 0, 23, 0],
};
const DAY_ORDER = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MAX_GUESTS = 20;   // keep equal to MAX_ONLINE_GUESTS in forms.py

document.addEventListener('DOMContentLoaded', () => {
    initNavbarScroll();
    initAnimatedCounters();
    initMenuFilter();
    initReservationWidget();
    initGalleryLightbox();
    initBusinessHoursStatus();
    initBackToTop();
});

/* 1. Navbar Scroll Effect */
function initNavbarScroll() {
    const navbar = document.querySelector('.custom-navbar');
    if (!navbar) return;

    const handleScroll = () => {
        navbar.classList.toggle('scrolled', window.scrollY > 40);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
}

/* 2. Animated Number Counters on Scroll */
function initAnimatedCounters() {
    const counters = document.querySelectorAll('.stat-number');
    if (!counters.length) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let hasRun = false;

    const readConfig = (el) => ({
        target: parseFloat(el.getAttribute('data-target')) || 0,
        prefix: el.getAttribute('data-prefix') || '',
        suffix: el.getAttribute('data-suffix') || '',
    });

    const animateValue = (el, end, duration, prefix, suffix) => {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            el.textContent = `${prefix}${Math.floor(progress * end)}${suffix}`;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                el.textContent = `${prefix}${end}${suffix}`;
            }
        };
        window.requestAnimationFrame(step);
    };

    const runCounters = () => {
        counters.forEach(counter => {
            const { target, prefix, suffix } = readConfig(counter);
            if (prefersReducedMotion) {
                counter.textContent = `${prefix}${target}${suffix}`;
            } else {
                animateValue(counter, target, 1800, prefix, suffix);
            }
        });
    };

    const statsSection = document.querySelector('.stats-bar') || counters[0].closest('section');
    if (!statsSection || !('IntersectionObserver' in window)) {
        runCounters();
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !hasRun) {
                hasRun = true;
                runCounters();
                observer.disconnect();
            }
        });
    }, { threshold: 0.25 });

    observer.observe(statsSection);
}

/* 3. Interactive Menu / Gallery Filter */
function initMenuFilter() {
    const filterButtons = document.querySelectorAll('.menu-tab-btn');
    const menuItems = document.querySelectorAll('.menu-grid-item');

    if (!filterButtons.length || !menuItems.length) return;

    // Remember each item's pending timer, so clicking quickly never leaves an item in the wrong state
    const timers = new WeakMap();
    const setTimer = (item, fn, delay) => {
        clearTimeout(timers.get(item));
        timers.set(item, setTimeout(fn, delay));
    };

    menuItems.forEach(item => {
        item.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
    });

    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const filterValue = btn.getAttribute('data-filter');

            menuItems.forEach(item => {
                const matches = filterValue === 'all' || item.getAttribute('data-category') === filterValue;

                if (matches) {
                    item.style.display = '';
                    // wait one frame so the fade-in actually animates
                    setTimer(item, () => {
                        item.style.opacity = '1';
                        item.style.transform = 'scale(1)';
                    }, 30);
                } else {
                    item.style.opacity = '0';
                    item.style.transform = 'scale(0.95)';
                    setTimer(item, () => {
                        item.style.display = 'none';
                    }, 250);
                }
            });
        });
    });
}

/* 4. Interactive Reservation Widget */
function initReservationWidget() {
    // Time slot button selection
    const timeSlotBtns = document.querySelectorAll('.time-slot-btn');
    const hiddenTimeInput = document.getElementById('selectedTimeSlot');

    timeSlotBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            timeSlotBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (hiddenTimeInput) {
                hiddenTimeInput.value = btn.textContent.trim();
            }
        });
    });

    // Guest counter increment/decrement
    const guestInput = document.getElementById('reservationGuests');
    const btnMinus = document.getElementById('btnGuestsMinus');
    const btnPlus = document.getElementById('btnGuestsPlus');

    if (guestInput && btnMinus && btnPlus) {
        const readGuests = () => parseInt(guestInput.value, 10) || 2;

        btnMinus.addEventListener('click', () => {
            guestInput.value = Math.max(1, readGuests() - 1);
        });

        btnPlus.addEventListener('click', () => {
            guestInput.value = Math.min(MAX_GUESTS, readGuests() + 1);
        });

        // If someone types a number, keep it inside the allowed range
        guestInput.addEventListener('change', () => {
            guestInput.value = Math.min(MAX_GUESTS, Math.max(1, readGuests()));
        });
    }

    // Home page quick-booking date: today up to 30 days ahead
    const quickDate = document.getElementById('quickDate');
    if (quickDate) {
        const fmt = (d) => [
            d.getFullYear(),
            String(d.getMonth() + 1).padStart(2, '0'),
            String(d.getDate()).padStart(2, '0'),
        ].join('-');
        const start = new Date();
        const end = new Date();
        end.setDate(start.getDate() + 30);
        quickDate.min = fmt(start);
        quickDate.max = fmt(end);
        if (!quickDate.value) quickDate.value = fmt(start);
    }

    // Date picker: no past dates, and start on today if empty
    // (the 30-day maximum is set in reservation.html and checked again by the server)
    const dateInput = document.getElementById('reservationDate');
    if (dateInput) {
        const now = new Date();
        const today = [
            now.getFullYear(),
            String(now.getMonth() + 1).padStart(2, '0'),
            String(now.getDate()).padStart(2, '0'),
        ].join('-');
        dateInput.min = today;
        if (!dateInput.value) {
            dateInput.value = today;
        }
    }
}

/* 5. Gallery Lightbox Modal */
function initGalleryLightbox() {
    const galleryItems = document.querySelectorAll('.gallery-item');
    const lightboxModal = document.getElementById('galleryLightboxModal');
    const lightboxImg = document.getElementById('lightboxModalImg');
    const lightboxCaption = document.getElementById('lightboxModalCaption');

    if (!galleryItems.length || !lightboxModal || !lightboxImg || !window.bootstrap) return;

    const modal = bootstrap.Modal.getOrCreateInstance(lightboxModal);

    const openItem = (item) => {
        const img = item.querySelector('img');
        if (!img) return;

        const title = item.querySelector('.gallery-title')?.textContent.trim() || '';
        const desc = item.querySelector('.gallery-desc')?.textContent.trim() || '';

        lightboxImg.src = img.src;
        lightboxImg.alt = img.alt || title || 'Restaurant gallery image';

        if (lightboxCaption) {
            // Build the caption with textContent (never innerHTML), so admin text can't inject HTML
            lightboxCaption.textContent = '';
            const strong = document.createElement('strong');
            strong.textContent = title;
            lightboxCaption.appendChild(strong);
            if (desc) {
                lightboxCaption.appendChild(document.createElement('br'));
                const small = document.createElement('small');
                small.className = 'text-muted';
                small.textContent = desc;
                lightboxCaption.appendChild(small);
            }
        }
        modal.show();
    };

    galleryItems.forEach(item => {
        // Make the tile reachable and usable with the keyboard
        item.setAttribute('tabindex', '0');
        item.setAttribute('role', 'button');
        item.setAttribute('aria-label', 'Open image preview');

        item.addEventListener('click', () => openItem(item));
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                openItem(item);
            }
        });
    });
}

/* 6. Live Business Hours Status Indicator */
function getRestaurantNow() {
    // Current weekday + time in the RESTAURANT's time zone (not the visitor's)
    try {
        const parts = new Intl.DateTimeFormat('en-US', {
            timeZone: RESTAURANT_TIMEZONE,
            weekday: 'short',
            hour: 'numeric',
            minute: 'numeric',
            hourCycle: 'h23',
        }).formatToParts(new Date());

        const get = (type) => parts.find(p => p.type === type)?.value;
        return {
            day: get('weekday'),
            minutes: (parseInt(get('hour'), 10) % 24) * 60 + parseInt(get('minute'), 10),
        };
    } catch (err) {
        const now = new Date();
        return { day: DAY_ORDER[now.getDay()], minutes: now.getHours() * 60 + now.getMinutes() };
    }
}

function formatClock(hour, minute) {
    const suffix = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 === 0 ? 12 : hour % 12;
    return `${hour12}:${String(minute).padStart(2, '0')} ${suffix}`;
}

function buildHoursMessage() {
    const { day, minutes } = getRestaurantNow();
    const [openH, openM, closeH, closeM] = OPENING_SCHEDULE[day] || [12, 0, 23, 0];
    const openAt = openH * 60 + openM;
    const closeAt = closeH * 60 + closeM;

    if (minutes >= openAt && minutes < closeAt) {
        return { isOpen: true, text: `Open Now • Closes ${formatClock(closeH, closeM)}` };
    }

    if (minutes < openAt) {
        return { isOpen: false, text: `Closed Now • Opens ${formatClock(openH, openM)}` };
    }

    // After closing: show tomorrow's opening time
    const nextDay = DAY_ORDER[(DAY_ORDER.indexOf(day) + 1) % 7];
    const [nOpenH, nOpenM] = OPENING_SCHEDULE[nextDay];
    return { isOpen: false, text: `Closed Now • Opens tomorrow ${formatClock(nOpenH, nOpenM)}` };
}

function initBusinessHoursStatus() {
    const statusBadges = document.querySelectorAll('.live-hours-status');
    if (!statusBadges.length) return;

    const render = () => {
        const { isOpen, text } = buildHoursMessage();

        statusBadges.forEach(badge => {
            badge.textContent = '';

            const span = document.createElement('span');
            span.className = isOpen
                ? 'badge bg-success-subtle text-success border border-success-subtle'
                : 'badge bg-danger-subtle text-danger border border-danger-subtle';

            const icon = document.createElement('i');
            icon.className = isOpen ? 'bi bi-circle-fill me-1' : 'bi bi-clock me-1';
            if (isOpen) icon.style.fontSize = '0.55rem';

            span.appendChild(icon);
            span.appendChild(document.createTextNode(' ' + text));
            badge.appendChild(span);
        });
    };

    render();
    setInterval(render, 60 * 1000);   // keep it fresh if the page stays open
}

/* 7. Back to Top Button */
function initBackToTop() {
    const backToTopBtn = document.getElementById('backToTopBtn');
    if (!backToTopBtn) return;

    const toggle = () => {
        const visible = window.scrollY > 350;
        // Both class names are toggled, so it works with either naming in style.css
        backToTopBtn.classList.toggle('show', visible);
        backToTopBtn.classList.toggle('visible', visible);
    };

    window.addEventListener('scroll', toggle, { passive: true });
    toggle();

    backToTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}
