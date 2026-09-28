const state = {
  token: localStorage.getItem('eve-token') || '',
  user: JSON.parse(localStorage.getItem('eve-user') || 'null'),
};

const $ = (id) => document.getElementById(id);
const messageBox = $('message-box');

function setMessage(text, type = 'success') {
  messageBox.textContent = text;
  messageBox.className = `message-box ${type}`;
  messageBox.classList.remove('hidden');
  clearTimeout(setMessage.timeoutId);
  setMessage.timeoutId = setTimeout(() => {
    messageBox.classList.add('hidden');
  }, 3000);
}

function updateUserUI() {
  const userPill = $('user-pill');
  const tokenBox = $('token-box');
  const tokenOutput = $('token-output');

  if (state.user) {
    userPill.textContent = `Signed in: ${state.user.email}`;
  } else {
    userPill.textContent = 'Not signed in';
  }

  if (state.token) {
    tokenBox.classList.remove('hidden');
    tokenOutput.value = state.token;
  } else {
    tokenBox.classList.add('hidden');
    tokenOutput.value = '';
  }
}

async function apiRequest(url, options = {}) {
  const defaultHeaders = { 'Content-Type': 'application/json' };
  const headers = { ...defaultHeaders, ...(options.headers || {}) };

  if (state.token && !headers.Authorization) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || 'Request failed');
  }

  return data;
}

async function fetchCentres() {
  const centres = await apiRequest('/diagnostic-centres');
  const list = $('centres-list');
  list.innerHTML = '';

  if (!centres.length) {
    list.innerHTML = '<li>No centres available.</li>';
    return;
  }

  centres.forEach((centre) => {
    const item = document.createElement('li');
    item.innerHTML = `<strong>${centre.name}</strong><br>${centre.location} <br>ID: ${centre.id}`;
    list.appendChild(item);
  });
}

async function fetchBookings() {
  if (!state.token) {
    $('bookings-list').innerHTML = '<li>Please login to view bookings.</li>';
    return;
  }

  try {
    const bookings = await apiRequest('/bookings');
    const list = $('bookings-list');
    list.innerHTML = '';

    if (!bookings.length) {
      list.innerHTML = '<li>No bookings found.</li>';
      return;
    }

    bookings.forEach((booking) => {
      const item = document.createElement('li');
      item.innerHTML = `ID: ${booking.id}<br>Patient: ${booking.patient_name}<br>Status: ${booking.status}<br>Amount: $${Number(booking.amount).toFixed(2)}`;
      list.appendChild(item);
    });
  } catch (error) {
    $('bookings-list').innerHTML = `<li>${error.message}</li>`;
  }
}

async function loadDashboard() {
  updateUserUI();
  try {
    await fetchCentres();
    await fetchBookings();
  } catch (error) {
    setMessage(error.message, 'error');
  }
}

$('signup-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = {
    email: $('signup-email').value,
    password: $('signup-password').value,
    role: $('signup-role').value,
  };

  try {
    const user = await apiRequest('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setMessage(`Account created for ${user.email}`);
    $('signup-form').reset();
  } catch (error) {
    setMessage(error.message, 'error');
  }
});

$('login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = {
    email: $('login-email').value,
    password: $('login-password').value,
  };

  try {
    const response = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    state.token = response.access_token;
    localStorage.setItem('eve-token', state.token);

    const me = await apiRequest('/auth/me');
    state.user = me;
    localStorage.setItem('eve-user', JSON.stringify(me));
    updateUserUI();
    await fetchBookings();
    setMessage('Signed in successfully');
    $('login-form').reset();
  } catch (error) {
    setMessage(error.message, 'error');
  }
});

$('centre-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await apiRequest('/diagnostic-centres', {
      method: 'POST',
      body: JSON.stringify({
        name: $('centre-name').value,
        location: $('centre-location').value,
      }),
    });
    $('centre-form').reset();
    await fetchCentres();
    setMessage('Centre created');
  } catch (error) {
    setMessage(error.message, 'error');
  }
});

$('test-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await apiRequest(`/diagnostic-centres/${$('test-centre-id').value}/tests`, {
      method: 'POST',
      body: JSON.stringify({
        name: $('test-name').value,
        price: Number($('test-price').value),
      }),
    });
    $('test-form').reset();
    setMessage('Test created');
  } catch (error) {
    setMessage(error.message, 'error');
  }
});

$('booking-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await apiRequest('/bookings', {
      method: 'POST',
      body: JSON.stringify({
        patient_name: $('booking-patient').value,
        centre_id: Number($('booking-centre-id').value),
        test_id: Number($('booking-test-id').value),
        appointment_datetime: new Date($('booking-datetime').value).toISOString(),
      }),
    });
    $('booking-form').reset();
    await fetchBookings();
    setMessage('Booking created successfully');
  } catch (error) {
    setMessage(error.message, 'error');
  }
});

$('payment-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const result = await apiRequest('/payments', {
      method: 'POST',
      body: JSON.stringify({
        booking_id: Number($('payment-booking-id').value),
        provider_event_id: $('payment-event-id').value,
        status: $('payment-status').value,
      }),
    });
    $('payment-form').reset();
    await fetchBookings();
    setMessage(`Payment ${result.payment_status} processed`);
  } catch (error) {
    setMessage(error.message, 'error');
  }
});

$('load-centres').addEventListener('click', async () => {
  await fetchCentres();
  await fetchBookings();
});

window.addEventListener('DOMContentLoaded', () => {
  updateUserUI();
  fetchCentres();
  fetchBookings();
});
