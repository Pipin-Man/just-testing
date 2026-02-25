const state = {
  categories: [],
  links: [],
  editingId: null,
};

const els = {
  categories: document.getElementById("categories"),
  messages: document.getElementById("messages"),
  linkForm: document.getElementById("link-form"),
  linkName: document.getElementById("link-name"),
  linkUrl: document.getElementById("link-url"),
  linkCategory: document.getElementById("link-category"),
  linkSubmit: document.getElementById("link-submit"),
  linkCancel: document.getElementById("link-cancel"),
  categoryForm: document.getElementById("category-form"),
  categoryName: document.getElementById("category-name"),
  categoryTemplate: document.getElementById("category-template"),
  linkTemplate: document.getElementById("link-template"),
};

function setMessage(msg = "") {
  els.messages.textContent = msg;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

async function loadData() {
  const [categories, links] = await Promise.all([
    api("/api/categories"),
    api("/api/links"),
  ]);

  state.categories = categories;
  state.links = links;

  renderCategoryOptions();
  renderBoard();
}

function renderCategoryOptions() {
  els.linkCategory.innerHTML = "";
  state.categories.forEach((category) => {
    const opt = document.createElement("option");
    opt.value = String(category.id);
    opt.textContent = category.name;
    els.linkCategory.appendChild(opt);
  });
}

function renderBoard() {
  els.categories.innerHTML = "";

  state.categories.forEach((category) => {
    const frag = els.categoryTemplate.content.cloneNode(true);
    const card = frag.querySelector(".category-card");
    const title = frag.querySelector("h3");
    const list = frag.querySelector(".link-list");
    const deleteBtn = frag.querySelector(".delete-category");

    title.textContent = category.name;
    deleteBtn.dataset.categoryId = String(category.id);

    const linksForCategory = state.links.filter(
      (link) => Number(link.category_id) === category.id
    );

    if (!linksForCategory.length) {
      const empty = document.createElement("li");
      empty.textContent = "No links yet.";
      empty.className = "empty";
      list.appendChild(empty);
    } else {
      linksForCategory.forEach((link) => {
        const linkFrag = els.linkTemplate.content.cloneNode(true);
        const a = linkFrag.querySelector("a");
        const editBtn = linkFrag.querySelector(".edit-link");
        const deleteLinkBtn = linkFrag.querySelector(".delete-link");

        a.href = link.url;
        a.textContent = link.name;
        a.title = link.url;

        editBtn.dataset.linkId = String(link.id);
        deleteLinkBtn.dataset.linkId = String(link.id);

        list.appendChild(linkFrag);
      });
    }

    els.categories.appendChild(card);
  });
}

function resetLinkForm() {
  state.editingId = null;
  els.linkForm.reset();
  if (state.categories.length > 0) {
    els.linkCategory.value = String(state.categories[0].id);
  }
  els.linkSubmit.textContent = "Add Link";
  els.linkCancel.classList.add("hidden");
}

async function handleLinkSubmit(event) {
  event.preventDefault();
  setMessage();

  const payload = {
    name: els.linkName.value.trim(),
    url: els.linkUrl.value.trim(),
    category_id: Number(els.linkCategory.value),
  };

  try {
    if (state.editingId) {
      await api(`/api/links/${state.editingId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    } else {
      await api("/api/links", { method: "POST", body: JSON.stringify(payload) });
    }

    await loadData();
    resetLinkForm();
  } catch (err) {
    setMessage(err.message);
  }
}

function beginEdit(linkId) {
  const link = state.links.find((item) => item.id === linkId);
  if (!link) return;

  state.editingId = link.id;
  els.linkName.value = link.name;
  els.linkUrl.value = link.url;
  els.linkCategory.value = String(link.category_id);
  els.linkSubmit.textContent = "Save Link";
  els.linkCancel.classList.remove("hidden");
}

async function handleBoardClick(event) {
  const editBtn = event.target.closest(".edit-link");
  const deleteLinkBtn = event.target.closest(".delete-link");
  const deleteCategoryBtn = event.target.closest(".delete-category");

  if (editBtn) {
    beginEdit(Number(editBtn.dataset.linkId));
    return;
  }

  try {
    if (deleteLinkBtn) {
      await api(`/api/links/${deleteLinkBtn.dataset.linkId}`, { method: "DELETE" });
      await loadData();
      if (state.editingId && String(state.editingId) === deleteLinkBtn.dataset.linkId) {
        resetLinkForm();
      }
      return;
    }

    if (deleteCategoryBtn) {
      await api(`/api/categories/${deleteCategoryBtn.dataset.categoryId}`, {
        method: "DELETE",
      });
      await loadData();
      return;
    }
  } catch (err) {
    setMessage(err.message);
  }
}

async function handleCategorySubmit(event) {
  event.preventDefault();
  setMessage();

  try {
    await api("/api/categories", {
      method: "POST",
      body: JSON.stringify({ name: els.categoryName.value.trim() }),
    });
    els.categoryForm.reset();
    await loadData();
  } catch (err) {
    setMessage(err.message);
  }
}

els.linkForm.addEventListener("submit", handleLinkSubmit);
els.linkCancel.addEventListener("click", resetLinkForm);
els.categoryForm.addEventListener("submit", handleCategorySubmit);
els.categories.addEventListener("click", handleBoardClick);

loadData().then(resetLinkForm).catch((err) => setMessage(err.message));
