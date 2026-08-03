const brandField = document.querySelector("#brand-input");
const brandSummary = document.querySelector("#s-brand");
const shareButton = document.querySelector("#share-link");
const openShare = document.querySelector("#open-share");
const orderForm = document.querySelector("#order-form");
const isWeChat = /MicroMessenger/i.test(navigator.userAgent);

function copyText(value) {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(value);
  const input = document.createElement("textarea");
  input.value = value;
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  input.remove();
  return Promise.resolve();
}

function showWeChatGuide(url) {
  let guide = document.querySelector("#wechat-share-guide");
  if (!guide) {
    guide = document.createElement("div");
    guide.id = "wechat-share-guide";
    guide.className = "wechat-share-guide";
    guide.innerHTML = `
      <button class="wechat-guide-backdrop" type="button" aria-label="关闭微信分享提示"></button>
      <section role="dialog" aria-modal="true" aria-labelledby="wechat-guide-title">
        <div class="wechat-guide-arrow">↗</div>
        <span class="wechat-guide-badge">微信好友代付</span>
        <h2 id="wechat-guide-title">点击右上角「···」</h2>
        <p>选择<strong>转发给朋友</strong>，好友收到后点击卡片即可打开代付详情。</p>
        <button class="wechat-copy-link" type="button">复制代付链接</button>
        <button class="wechat-guide-close" type="button">我知道了</button>
      </section>`;
    document.body.appendChild(guide);
    guide.querySelector(".wechat-guide-backdrop").addEventListener("click", () => guide.classList.remove("show"));
    guide.querySelector(".wechat-guide-close").addEventListener("click", () => guide.classList.remove("show"));
  }
  guide.querySelector(".wechat-copy-link").onclick = async () => {
    await copyText(url);
    setNotice("代付链接已复制，可粘贴发送给微信或 QQ 好友。");
    guide.classList.remove("show");
  };
  guide.classList.add("show");
}

async function shareOrder(url, service, amount) {
  if (isWeChat) {
    showWeChatGuide(url);
    return;
  }
  if (navigator.share) {
    try {
      await navigator.share({
        title: `${brandField.value.trim()}｜好友代付`,
        text: `${service}，金额 ¥${amount.toFixed(2)}，请帮我完成代付。`,
        url
      });
      setNotice("已打开系统分享面板，请选择微信或 QQ 好友。当前为演示链接，不会扣款。");
      return;
    } catch (error) {
      if (error?.name === "AbortError") {
        setNotice("已取消分享，代付链接仍可继续使用。");
        return;
      }
    }
  }
  await copyText(url);
  setNotice("代付链接已复制。请打开微信或 QQ，粘贴发送给好友。");
}

brandField.addEventListener("input", () => {
  brandSummary.textContent = brandField.value.trim() || "待填写自有品牌";
});

orderForm.addEventListener("submit", event => {
  const amountValue = Number(document.querySelector("#amount").value);
  if (!brandField.value.trim()) {
    event.preventDefault();
    event.stopImmediatePropagation();
    setNotice("请填写你的自有品牌名称，并确保页面同时展示真实收款主体。");
    return;
  }
  if (!Number.isFinite(amountValue) || amountValue < 9.9 || amountValue > 520) {
    event.preventDefault();
    event.stopImmediatePropagation();
    setNotice("订单金额须在 ¥9.90 至 ¥520.00 之间。");
    return;
  }
  window.setTimeout(() => {
    if (!document.querySelector("#cashier").disabled) shareButton.disabled = false;
  }, 0);
}, true);

shareButton.addEventListener("click", async () => {
  const amountValue = Number(document.querySelector("#amount").value);
  const service = document.querySelector("#service").value.trim();
  const query = new URLSearchParams({
    brand: brandField.value.trim(),
    merchant: document.querySelector("#merchant").value.trim(),
    service,
    amount: amountValue.toFixed(2),
    refund: document.querySelector("#refund").value.trim(),
    order: `OD${Date.now().toString().slice(-10)}`,
    expires: String(Date.now() + 15 * 60 * 1000)
  });
  const url = new URL("./pay.html", location.href);
  url.search = query.toString();
  openShare.href = url.href;
  openShare.hidden = false;
  await shareOrder(url.href, service, amountValue);
});
