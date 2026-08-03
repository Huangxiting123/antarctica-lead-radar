const params = new URLSearchParams(location.search);
const get = (key, fallback) => (params.get(key) || fallback).slice(0, 120);
const brand = get("brand", "好友代付");
const merchant = get("merchant", "待核验收款主体");
const service = get("service", "待核验订单内容");
const refund = get("refund", "请联系商户确认退款规则");
const order = get("order", "DEMO-ORDER");
const amount = Math.min(520, Math.max(9.9, Number(params.get("amount")) || 9.9));
const expires = Number(params.get("expires")) || Date.now() + 15 * 60 * 1000;
const money = value => new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY" }).format(value);
const message = document.querySelector("#p-message");
const isWeChat = /MicroMessenger/i.test(navigator.userAgent);

document.title = `${brand}｜好友代付 ${money(amount)}`;
document.querySelector("#p-brand-head").textContent = brand;
document.querySelector("#p-brand").textContent = brand;
document.querySelector("#p-merchant").textContent = merchant;
document.querySelector("#p-service").textContent = service;
document.querySelector("#p-refund").textContent = refund;
document.querySelector("#p-order").textContent = order;
document.querySelector("#p-amount").textContent = money(amount);

const time = document.querySelector("#p-time");
function tick() {
  const left = Math.max(0, Math.ceil((expires - Date.now()) / 1000));
  time.textContent = left ? `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}` : "已过期";
  time.classList.toggle("expired", !left);
}
tick();
setInterval(tick, 1000);

const details = document.querySelector("#p-details");
const detailList = document.querySelector("#p-dl");
details.addEventListener("click", () => {
  const open = detailList.classList.toggle("open");
  details.textContent = open ? "收起详情" : "查看详情";
});

document.querySelectorAll("[data-channel]").forEach(button => button.addEventListener("click", () => {
  message.hidden = false;
  message.textContent = `${button.dataset.channel}尚未开通。当前页面仅用于确认代付样式，不会发起扣款。商户完成认证后才会跳转官方收银台。`;
}));

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

function showWeChatGuide() {
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
        <p>选择<strong>转发给朋友</strong>，微信会把本页作为卡片链接发送给好友。</p>
        <button class="wechat-copy-link" type="button">复制代付链接</button>
        <button class="wechat-guide-close" type="button">我知道了</button>
      </section>`;
    document.body.appendChild(guide);
    guide.querySelector(".wechat-guide-backdrop").addEventListener("click", () => guide.classList.remove("show"));
    guide.querySelector(".wechat-guide-close").addEventListener("click", () => guide.classList.remove("show"));
    guide.querySelector(".wechat-copy-link").addEventListener("click", async () => {
      await copyText(location.href);
      message.hidden = false;
      message.textContent = "代付链接已复制，可粘贴发送给微信或 QQ 好友。";
      guide.classList.remove("show");
    });
  }
  guide.classList.add("show");
}

document.querySelector("#p-share").addEventListener("click", async () => {
  if (isWeChat) {
    showWeChatGuide();
    return;
  }
  if (navigator.share) {
    try {
      await navigator.share({
        title: `${brand}｜好友代付`,
        text: `${service}，金额 ${money(amount)}，请帮我完成代付。`,
        url: location.href
      });
      return;
    } catch (error) {
      if (error?.name === "AbortError") return;
    }
  }
  await copyText(location.href);
  message.hidden = false;
  message.textContent = "代付链接已复制。请打开微信或 QQ，粘贴发送给好友。";
});
