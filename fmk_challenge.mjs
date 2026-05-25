const targetUrl = process.argv[2] || "https://www.fmkorea.com/hotdeal";
const userAgent = process.argv[3] || "Chrome";

const response = await fetch(targetUrl, {
  headers: {
    "User-Agent": userAgent,
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
  },
});
const body = await response.text();

const token = body.match(/escape\('([^']+)'\)/)?.[1];
const fm5Args = body.match(/fm5\('([^']+)'\s*,\s*'([^']+)'\)/);
if (!token || !fm5Args) {
  process.exit(2);
}

const cookies = new Map();
const documentShim = {
  get cookie() {
    return Array.from(cookies.entries())
      .map(([name, value]) => `${name}=${value}`)
      .join("; ");
  },
  set cookie(cookieValue) {
    const firstPart = cookieValue.split(";", 1)[0];
    const separator = firstPart.indexOf("=");
    if (separator <= 0) return;
    cookies.set(firstPart.slice(0, separator), firstPart.slice(separator + 1));
  },
};

class WindowShim {}
const windowShim = new WindowShim();
windowShim.document = documentShim;

globalThis.Window = WindowShim;
globalThis.window = windowShim;
globalThis.self = windowShim;
globalThis.document = documentShim;

documentShim.cookie = `lite_year=${escape(token)}`;
documentShim.cookie = `g_lite_year=${escape(token)}`;

const moduleSource = await (await fetch("https://www.fmkorea.com/mc/mc.php")).text();
const moduleUrl = `data:text/javascript;base64,${Buffer.from(moduleSource).toString("base64")}`;
const module = await import(moduleUrl);
await module.default("https://www.fmkorea.com/mc/mcw.php");
module.fm5(fm5Args[1], fm5Args[2]);

console.log(documentShim.cookie);
