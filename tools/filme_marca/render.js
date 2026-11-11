// Renderiza filme.html quadro a quadro (determinístico) e entrega PNGs ao FFmpeg.
// Uso: node tools/filme_marca/render.js SAIDA.mp4 [--w 1080] [--h 1080] [--fps 59.94] [--audio som.wav] [--dur 30] [--dados textos.json --mapa mapa_reel.json]  (com --mapa, --preview recebe segundos) [--preview 0,80,135,230]
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const saida = args[0];
const W = +opt("w", 1080), H = +opt("h", 1080);
const FPS = opt("fps", "59.94");
const audio = opt("audio", null);
const preview = opt("preview", null);
const TIMELINE = 29.97, BASE = 12;
function quadro(t) {                                   // segundo do vídeo -> quadro da timeline
  if (!mapa) return t * TIMELINE * (BASE / DUR);
  const a = mapa.ancoras;
  for (let i = 1; i < a.length; i++) if (t <= a[i][0]) {
    const [t0, f0] = a[i - 1], [t1, f1] = a[i];
    return f0 + (f1 - f0) * (t - t0) / (t1 - t0);
  }
  return a[a.length - 1][1];
}
const dados = opt("dados", null);                     // JSON com os textos do Reel
const mapa = opt("mapa", null) ? JSON.parse(fs.readFileSync(opt("mapa", null), "utf8")) : null;
const DUR = mapa ? mapa.duracao : +opt("dur", 12);           // duração final; o filme é esticado de forma uniforme (ex.: --dur 30)

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.resolve(__dirname, "filme.html"));
  await page.evaluate(([w, h]) => window.setup(w, h), [W, H]);
  if (dados) await page.evaluate(d => window.setTexts(d), JSON.parse(fs.readFileSync(dados, "utf8")));
  await page.evaluate(() => document.fonts.ready);
  if (preview) {
    fs.mkdirSync(saida, { recursive: true });
    for (const f of preview.split(",").map(Number)) {
      await page.evaluate(x => window.renderFrame(x), mapa ? quadro(f) : f);
      await page.screenshot({ path: path.join(saida, `previa_f${String(f).padStart(3, "0")}.png`) });
    }
    await browser.close();
    return;
  }
  const fpsNum = FPS === "59.94" ? 60000 / 1001 : +FPS;
  const n = Math.round(DUR * fpsNum);
  const rate = FPS === "59.94" ? "60000/1001" : FPS;
  const ff = ["-y", "-v", "error", "-f", "image2pipe", "-framerate", rate, "-c:v", "png", "-i", "-"];
  if (audio) ff.push("-i", audio);
  ff.push("-map", "0:v");
  if (audio) ff.push("-map", "1:a", "-c:a", "aac", "-b:a", "256k", "-ar", "48000");
  ff.push("-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
          "-r", rate, "-movflags", "+faststart", "-t", String(DUR), saida);
  const p = spawn("ffmpeg", ff, { stdio: ["pipe", "inherit", "inherit"] });
  for (let i = 0; i < n; i++) {
    const f = quadro(i / fpsNum);            // quadro da linha do tempo de 29,97 fps (fracionário no master 59,94)
    await page.evaluate(x => window.renderFrame(x), f);
    const png = await page.screenshot({ type: "png" });
    if (!p.stdin.write(png)) await new Promise(r => p.stdin.once("drain", r));
  }
  p.stdin.end();
  await new Promise(r => p.on("close", r));
  await browser.close();
})();
