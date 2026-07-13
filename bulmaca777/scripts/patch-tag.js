import { readFileSync, writeFileSync } from "fs";

let s = readFileSync("scripts/write-utf8-html.js", "utf8");
s = s.replace(
  /return html\.replace\([^;]+\);/,
  'return html.replace(/<TAG/g, "<div").replace(/<\\/TAG>/g, "</div>");'
);
writeFileSync("scripts/write-utf8-html.js", s, "utf8");
console.log("patched");
