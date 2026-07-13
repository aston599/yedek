const params = new URLSearchParams(location.search);
const redirect = params.get("next") || "/admin/";

const errorEl = document.getElementById("error");

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.remove("hidden");
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.dataset.tab;
    document.getElementById("formLogin").classList.toggle("hidden", tab !== "login");
    document.getElementById("formRegister").classList.toggle("hidden", tab !== "register");
    errorEl.classList.add("hidden");
  });
});

async function submitAuth(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Islem basarisiz");
  return data;
}

document.getElementById("formLogin").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await submitAuth("/api/auth/login", {
      username: fd.get("username"),
      password: fd.get("password"),
    });
    location.href = redirect;
  } catch (err) {
    showError(err.message);
  }
});

document.getElementById("formRegister").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await submitAuth("/api/auth/register", {
      username: fd.get("username"),
      password: fd.get("password"),
    });
    location.href = redirect;
  } catch (err) {
    showError(err.message);
  }
});

fetch("/api/auth/me", { credentials: "include" })
  .then((r) => r.json())
  .then((d) => {
    if (d.user) location.href = redirect;
  });
