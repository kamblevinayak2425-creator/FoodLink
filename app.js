document.addEventListener('DOMContentLoaded', () => {
  const roleSelect = document.querySelector('select[name="role"]');
  if (roleSelect) {
    const labels = {
      donor: 'Restaurant / food business (donate surplus food)',
      ngo: 'NGO / community organization (receive food)',
      consumer: 'Community member (receive food)',
    };
    Object.entries(labels).forEach(([value, label]) => {
      const option = roleSelect.querySelector(`option[value="${value}"]`);
      if (option) option.textContent = label;
    });
    if (new URLSearchParams(window.location.search).get('role') === 'donor') {
      roleSelect.value = 'donor';
    }
    const intro = document.querySelector('.auth-intro');
    if (intro && window.location.pathname === '/register') {
      intro.textContent = 'Restaurants and food businesses donate surplus. NGOs and community members sign up to find and request food.';
    }
  }

  document.querySelector('.hero-actions .btn-outline-green')?.setAttribute('href', '/donate-food');

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
  if (csrfToken) {
    document.querySelectorAll('form[method="post"], form:not([method])').forEach((form) => {
      if (!form.querySelector('input[name="csrf_token"]')) {
        const token = document.createElement('input');
        token.type = 'hidden';
        token.name = 'csrf_token';
        token.value = csrfToken;
        form.append(token);
      }
    });
  }

  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;
      const showing = input.type === 'password';
      input.type = showing ? 'text' : 'password';
      button.innerHTML = `<i class="fa-regular fa-eye${showing ? '-slash' : ''}"></i>`;
      button.setAttribute('aria-label', showing ? 'Hide password' : 'Show password');
    });
  });

  document.querySelectorAll('form[data-validate]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });

  const imageInput = document.getElementById('food-image');
  const preview = document.getElementById('image-preview');
  imageInput?.addEventListener('change', () => {
    const file = imageInput.files?.[0];
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      imageInput.value = '';
      window.foodlinkToast?.('Choose a JPG, PNG, or WebP image smaller than 5 MB.', 'error');
      return;
    }
    preview.src = URL.createObjectURL(file);
    preview.classList.remove('d-none');
  });

  const donationType = document.getElementById('donation-type');
  const price = document.getElementById('food-price');
  const syncPrice = () => {
    if (!donationType || !price) return;
    price.disabled = donationType.value === 'Free';
    if (price.disabled) price.value = '0';
  };
  donationType?.addEventListener('change', syncPrice);
  syncPrice();

  const timeline = document.querySelector('.timeline');
  if (timeline) {
    const states = ['Available', 'Requested', 'Approved', 'Ready for Pickup', 'Collected', 'Completed'];
    const activeIndex = states.indexOf(timeline.dataset.status);
    timeline.querySelectorAll('.timeline-step').forEach((step, index) => {
      if (index < activeIndex) step.classList.add('is-complete');
      if (index === activeIndex) step.classList.add('is-current');
    });
    if (timeline.dataset.status === 'Cancelled') {
      timeline.querySelectorAll('.timeline-step')[1]?.classList.add('is-cancelled');
    }
  }

  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const submitter = event.submitter;
      const message = submitter?.dataset.confirm || form.dataset.confirm;
      if (message && !window.confirm(message)) event.preventDefault();
    });
  });

  const categories = window.foodlinkCategories;
  const canvas = document.getElementById('categoryChart');
  if (canvas && window.Chart) {
    const palette = ['#4e8d61', '#df9b77', '#ddc76d', '#7ea9a2', '#9cba8c', '#cf8165'];
    new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: (categories || []).map((item) => item[0]),
        datasets: [{ data: (categories || []).map((item) => item[1]), backgroundColor: palette, borderColor: '#fff', borderWidth: 4, hoverOffset: 5 }],
      },
      options: { maintainAspectRatio: false, cutout: '67%', plugins: { legend: { position: 'right', labels: { usePointStyle: true, pointStyle: 'circle', boxWidth: 7, padding: 15, font: { family: 'DM Sans', size: 10 } } } } },
    });
  }

  const monthlyCanvas = document.getElementById('monthlyChart');
  if (monthlyCanvas && window.Chart) {
    new Chart(monthlyCanvas, {
      type: 'line',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        datasets: [{ data: window.foodlinkMonthly || [], borderColor: '#4e8d61', backgroundColor: 'rgba(78,141,97,.12)', fill: true, tension: .35, pointRadius: 3, pointBackgroundColor: '#4e8d61' }],
      },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#edf1ed' }, ticks: { precision: 0, font: { family: 'DM Sans', size: 9 } } }, x: { grid: { display: false }, ticks: { font: { family: 'DM Sans', size: 9 } } } } },
    });
  }
});

window.foodlinkToast = (message, kind = 'success') => {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-bg-${kind === 'error' ? 'danger' : 'success'} border-0`;
  toast.role = 'status';
  toast.innerHTML = `<div class="d-flex"><div class="toast-body"></div><button class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
  toast.querySelector('.toast-body').textContent = message;
  container.append(toast);
  bootstrap.Toast.getOrCreateInstance(toast, { delay: 3500 }).show();
};
