(function () {
  function pathToPage(pathname) {
    var clean = (pathname || "/").replace(/\/+$/, "") || "/";
    var mapping = {
      "/": "home",
      "/products": "catalog",
      "/login": "login",
      "/register": "register",
      "/cart": "cart",
      "/checkout": "checkout",
      "/admin": "admin",
      "/orders": "orders"
    };
    return mapping[clean] || "home";
  }

  function mergeProductsFromServer(serverProducts) {
    var baseProducts = Array.isArray(PRODUCTS) ? PRODUCTS : [];
    var baseIds = new Set(baseProducts.map(function (p) { return String(p.id); }));
    var extras = (serverProducts || []).filter(function (p) {
      return !baseIds.has(String(p.id));
    });
    return { base: baseProducts, extras: extras };
  }

  async function serverRequest(url, options) {
    var response = await fetch(url, Object.assign({
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" }
    }, options || {}));
    var payload = await response.json();
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.message || "Error de servidor");
    }
    return payload;
  }

  function syncLocalMirror(payload) {
    var merged = mergeProductsFromServer(payload.products || []);
    window.__serverExtraProducts = merged.extras;
    window.__serverOrders = payload.orders || [];
    window.__serverAdminOrders = payload.adminOrders || [];
    window.__serverUsers = payload.users || [];
    window.__serverTickets = payload.tickets || [];

    currentUser = payload.currentUser || null;
    cart = payload.cart || [];

    if (currentUser) {
      localStorage.setItem("tempest_user", JSON.stringify(currentUser));
    } else {
      localStorage.removeItem("tempest_user");
    }
    localStorage.setItem("tempest_users", JSON.stringify(window.__serverUsers));
    localStorage.setItem("tempest_orders", JSON.stringify(currentUser && currentUser.role === "admin" ? window.__serverAdminOrders : window.__serverOrders));
    localStorage.setItem("vendor_products", JSON.stringify(window.__serverExtraProducts));
    localStorage.setItem("tempest_support_tickets", JSON.stringify(window.__serverTickets));

    renderUserArea();
    updateCartBadge();
    updateHeroBtn();
  }

  async function refreshServerState() {
    var payload = await serverRequest("/api/bootstrap", { method: "GET", headers: {} });
    syncLocalMirror(payload);
    return payload;
  }

  function getAllProducts() {
    var baseProducts = Array.isArray(PRODUCTS) ? PRODUCTS : [];
    var extras = Array.isArray(window.__serverExtraProducts) ? window.__serverExtraProducts : [];
    return baseProducts.concat(extras);
  }

  function initDemoData() {
    return;
  }

  async function doLogin() {
    var email = (document.getElementById("loginEmail") || {}).value || "";
    var password = (document.getElementById("loginPassword") || {}).value || "";
    email = email.trim();
    if (!email || !password) {
      toast("Completa todos los campos", "error");
      return;
    }
    try {
      await serverRequest("/api/login", {
        method: "POST",
        body: JSON.stringify({ email: email, password: password })
      });
      await refreshServerState();
      toast("Sesion iniciada");
      navigate(currentUser && currentUser.role === "admin" ? "admin" : "home");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function doRegister() {
    var name = ((document.getElementById("reg-name") || {}).value || "").trim();
    var email = ((document.getElementById("reg-email") || {}).value || "").trim();
    var password = (document.getElementById("reg-password") || {}).value || "";
    var role = ((document.getElementById("reg-role") || {}).value || "cliente").trim();
    var phone = ((document.getElementById("reg-phone") || {}).value || "").trim();
    var address = ((document.getElementById("reg-address") || {}).value || "").trim();
    var adminPass = (document.getElementById("reg-adminpass") || {}).value || "";
    try {
      await serverRequest("/api/register", {
        method: "POST",
        body: JSON.stringify({
          name: name,
          email: email,
          password: password,
          role: role,
          phone: phone,
          address: address,
          adminPass: adminPass
        })
      });
      await refreshServerState();
      toast("Registro exitoso");
      navigate("home");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function doLogout() {
    try {
      await serverRequest("/api/logout", { method: "POST", body: JSON.stringify({}) });
      await refreshServerState();
      toast("Sesion cerrada");
      navigate("home");
      closeDropdown();
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function addToCart(product, size, color) {
    if (!currentUser) {
      toast("Debes iniciar sesion", "error");
      navigate("login");
      return;
    }
    try {
      await serverRequest("/api/cart/add", {
        method: "POST",
        body: JSON.stringify({
          productId: String(product.id),
          selectedSize: size || (product.sizes && product.sizes[0]) || "M",
          selectedColor: color || "",
          quantity: 1
        })
      });
      await refreshServerState();
      toast(product.name + " agregado al carrito");
      if (currentPage === "cart") {
        renderCart();
      }
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function removeFromCart(id, size, color) {
    try {
      await serverRequest("/api/cart/remove", {
        method: "POST",
        body: JSON.stringify({
          productId: String(id),
          selectedSize: size || "M",
          selectedColor: color || ""
        })
      });
      await refreshServerState();
      toast("Producto eliminado");
      if (currentPage === "cart") {
        renderCart();
      }
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function placeOrder() {
    var name = ((document.getElementById("del-name") || {}).value || "").trim();
    var city = ((document.getElementById("del-city") || {}).value || "").trim();
    var address = ((document.getElementById("del-address") || {}).value || "").trim();
    if (!name || !city || !address) {
      toast("Completa los datos de entrega", "error");
      return;
    }
    var btn = document.getElementById("placeOrderBtn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "PROCESANDO...";
    }
    try {
      await serverRequest("/api/checkout", {
        method: "POST",
        body: JSON.stringify({
          name: name,
          city: city,
          address: address,
          paymentMethod: activePaymentMethod
        })
      });
      await refreshServerState();
      toast("Pedido realizado con exito");
      navigate("ordersuccess");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "CONFIRMAR PEDIDO";
      }
    }
  }

  async function adminAddProduct() {
    var name = ((document.getElementById("adm-name") || {}).value || "").trim();
    var price = ((document.getElementById("adm-price") || {}).value || "").trim();
    var description = ((document.getElementById("adm-desc") || {}).value || "").trim();
    var image = ((document.getElementById("adm-image") || {}).value || "").trim();
    var category = ((document.getElementById("adm-cat") || {}).value || "Tops").trim();
    var gender = ((document.getElementById("adm-gender") || {}).value || "Unisex").trim();
    var sizes = ((document.getElementById("adm-sizes") || {}).value || "S, M, L, XL").trim();
    if (!name || !price || !description || !image) {
      toast("Completa los campos obligatorios", "error");
      return;
    }
    try {
      await serverRequest("/api/admin/products", {
        method: "POST",
        body: JSON.stringify({
          name: name,
          price: price,
          description: description,
          image: image,
          category: category,
          gender: gender,
          sizes: sizes.replace(/\s+/g, "")
        })
      });
      await refreshServerState();
      toast("Producto agregado");
      adminSection("products", null);
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function adminDeleteProduct(id) {
    try {
      await serverRequest("/api/admin/products/" + encodeURIComponent(String(id)), {
        method: "DELETE",
        headers: {}
      });
      await refreshServerState();
      toast("Producto eliminado");
      adminSection("products", null);
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function serverInit() {
    try {
      await refreshServerState();
      var page = pathToPage(window.location.pathname);
      navigate(page);
      if (page === "admin" && currentUser && currentUser.role === "admin") {
        adminSection("dashboard", null);
      }
    } catch (error) {
      console.error(error);
    }
  }

  serverInit();
})();
