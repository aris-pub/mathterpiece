// Typesetting a formula's LaTeX with MathJax (mtp-bz6h). MathJax 3's SVG output carries its
// fonts in its own code, so a page opened as a file, which fetches nothing, still typesets, and
// it typesets at once, with nothing to wait for. \term{name}{…} is MathJax's own \class, with a
// prefixed class name, so the illustrator's LaTeX goes to MathJax as written.
import { browserAdaptor } from "mathjax-full/js/adaptors/browserAdaptor.js";
import { RegisterHTMLHandler } from "mathjax-full/js/handlers/html.js";
import "mathjax-full/js/input/tex/ams/AmsConfiguration.js";
import "mathjax-full/js/input/tex/base/BaseConfiguration.js";
import "mathjax-full/js/input/tex/boldsymbol/BoldsymbolConfiguration.js";
import "mathjax-full/js/input/tex/braket/BraketConfiguration.js";
import "mathjax-full/js/input/tex/cancel/CancelConfiguration.js";
import "mathjax-full/js/input/tex/color/ColorConfiguration.js";
import "mathjax-full/js/input/tex/configmacros/ConfigMacrosConfiguration.js";
import "mathjax-full/js/input/tex/html/HtmlConfiguration.js";
import "mathjax-full/js/input/tex/mathtools/MathtoolsConfiguration.js";
import "mathjax-full/js/input/tex/newcommand/NewcommandConfiguration.js";
import { TeX } from "mathjax-full/js/input/tex.js";
import { mathjax } from "mathjax-full/js/mathjax.js";
import { SVG } from "mathjax-full/js/output/svg.js";

/** The class MathJax gives the element of a term. */
export const termClass = (name: string): string => `mtp-term-${name}`;

const PACKAGES = ["base", "ams", "newcommand", "configmacros", "html", "boldsymbol", "braket", "cancel", "color", "mathtools"];

type Typesetter = { convert: (latex: string, display: boolean) => Element };
let typesetter: Typesetter | null = null;

function start(): Typesetter {
  const adaptor = browserAdaptor();
  RegisterHTMLHandler(adaptor);
  const tex = new TeX({ packages: PACKAGES, macros: { term: [`\\class{${termClass("#1")}}{#2}`, 2] } });
  // Each formula keeps its own glyphs, so two displays, or a copy of one, never share them by id.
  const svg = new SVG({ fontCache: "local" });
  // A fragment, not the page itself: MathJax only converts strings here, and never searches the
  // page for math.
  const doc = mathjax.document(document.createDocumentFragment(), { InputJax: tex, OutputJax: svg });
  document.head.appendChild(svg.styleSheet(doc) as unknown as Node);
  return { convert: (latex, display) => doc.convert(latex, { display }) as Element };
}

/** The LaTeX typeset, as an mjx-container holding an SVG. */
export function typeset(latex: string, display: boolean): Element {
  typesetter ??= start();
  return typesetter.convert(latex, display);
}

const MARK = /\\term\s*\{([^{}]*)\}\s*\{/y;

/** The LaTeX to typeset: the formula's, with each term's content in place of what the LaTeX
 * marks when content gives one, and each term that does not exist left out with what it holds,
 * so the formula closes up around it. */
export function latexOf(
  tex: string,
  content: (term: string) => string | undefined,
  exists: (term: string) => boolean,
): string {
  let out = "";
  let k = 0;
  while (k < tex.length) {
    MARK.lastIndex = k;
    const found = MARK.exec(tex);
    if (found) {
      const name = found[1]!;
      const start = MARK.lastIndex;
      const end = closing(tex, start);
      const own = content(name);
      if (exists(name)) out += `\\term{${name}}{${own ?? latexOf(tex.slice(start, end), content, exists)}}`;
      k = end + 1;
    } else if (tex[k] === "\\") {
      out += tex.slice(k, k + 2);
      k += 2;
    } else {
      out += tex[k];
      k += 1;
    }
  }
  return out;
}

/** Where the group starting at start closes: the index of its "}". The compiler has checked
 * the braces match. */
function closing(tex: string, start: number): number {
  let depth = 1;
  for (let k = start; k < tex.length; k++) {
    if (tex[k] === "\\") k++;
    else if (tex[k] === "{") depth++;
    else if (tex[k] === "}" && --depth === 0) return k;
  }
  return tex.length;
}
