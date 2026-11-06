;;; mtp-mode.el --- Major mode for mathterpiece .mtp files -*- lexical-binding: t; -*-

;; Load it from your init file:
;;   (load "/path/to/mathterpiece/editors/mtp-mode.el")
;; Files ending in .mtp then open in mtp-mode.

;;; Code:

(require 'lisp-mode)

(defconst mtp-mode--heads
  '("scene" "group" "row" "column" "motif" "variant" "type" "func" "import"
    "circle" "rect" "ellipse" "line" "triangle" "polyline" "polygon" "arc" "ring" "text" "curve"
    "real" "int" "ratio" "complex" "bool" "string" "point" "list" "transform"
    "color" "font" "namespace" "palette" "interface" "colormap"
    "transition" "move" "wait" "animation" "at-once" "in-order"
    "canvas" "readout" "slider" "button" "play" "toggle" "on-drag" "on-click"
    "on-release" "on-dragend" "on-view" "on-enter" "on-leave" "on-pointermove"
    "defaults" "clip" "loop" "autoplay" "exists-when"
    "foreach" "let" "fn" "if" "cond" "and" "or" "when" "else" "name" "as" "like")
  "Heads of mtp's forms. Any of them may end in an underscore, as in (circle_ …).")

(defconst mtp-mode--arguments
  '("a" "active" "align" "autoplay" "b" "background" "buttons" "c" "clip" "controls" "dash" "dash-offset"
    "doc" "duration" "ease" "family" "fill" "fill-opacity" "fixed-size" "font" "from" "gap"
    "halign" "height"
    "label" "like" "line-cap" "line-join" "num" "opacity" "pan" "path" "points"
    "pointer-events" "pos" "r" "rx"
    "ry" "size" "step" "stop-propagation" "stroke" "stroke-opacity" "stroke-width" "style" "to" "toggle-duration" "toggle-ease" "transform"
    "translate" "valign" "value" "weight" "width"
    "x" "y" "zoom")
  "Keyword arguments: the heads of the forms a form takes as its optional arguments,
such as (x -8), (duration 0.8) and (fill teal).")

(defface mtp-mode-head-face
  '((t :inherit font-lock-type-face :weight bold))
  "Face for the heads of mtp's forms, such as canvas in (canvas view …). Most heads are types,
as circle and real are, and themes draw the type color strongly and apart from the keyword
color, which keyword arguments take.")

(defface mtp-mode-doc-face
  '((t :inherit font-lock-string-face :weight bold :slant italic))
  "Face for a docstring, the text of doc@'text'. Themes often draw `font-lock-doc-face' faint,
so it takes the string color, which every theme draws clearly, in bold italic to stand out
from the figure's own strings.")

(defconst mtp-mode--indent
  '(;; Forms with a name: the name, then their positional arguments, then their body.
    ("scene" . 1) ("group" . 1) ("row" . 1) ("column" . 1) ("circle" . 1) ("rect" . 1) ("ellipse" . 1) ("line" . 1)
    ("triangle" . 1) ("polyline" . 1) ("polygon" . 1) ("curve" . 1) ("arc" . 1) ("ring" . 1) ("text" . 2) ("font" . 1)
    ("namespace" . 1) ("palette" . 1) ("interface" . 1) ("colormap" . 2)
    ("real" . 2) ("int" . 2) ("ratio" . 2) ("complex" . 2) ("bool" . 2) ("string" . 2)
    ("point" . 2) ("list" . 2) ("transform" . 2) ("color" . 2)
    ("type" . 2) ("motif" . 2) ("variant" . 2) ("func" . 2)
    ("transition" . 2) ("animation" . 1)
    ("canvas" . 1) ("readout" . 2) ("slider" . 2) ("button" . 1) ("play" . 1) ("toggle" . 2)
    ;; Forms with no name.
    ("move" . 1) ("at-once" . 0) ("in-order" . 0) ("on-drag" . 2) ("on-click" . 1)
    ("on-release" . 1) ("on-dragend" . 1) ("on-view" . 1) ("on-enter" . 1) ("on-leave" . 1)
    ("on-pointermove" . 2) ("defaults" . 0)
    ("exists-when" . 1)
    ("when" . 1) ("foreach" . 2) ("let" . 1) ("fn" . 1) ("if" . 2))
  "How many positional arguments each form takes before its body, counting its name.
Their lines are indented 4; the body's, 2, as for Emacs Lisp's own forms.")

(defconst mtp-mode--keywords
  (let ((group '("doc" "defaults" "clip" "fixed-size" "translate" "transform" "gap" "align"
                 "opacity" "fill" "stroke" "stroke-width" "fill-opacity" "stroke-opacity" "dash"
                 "line-cap" "line-join" "x" "y" "pos"))
        (animation '("loop" "duration" "ease" "defaults")))
    `(("scene" "doc" "background" "transform")
      ("group" ,@group) ("row" ,@group) ("column" ,@group)
      ("canvas" "doc" "x" "y" "width" "height" "transform" "pan" "zoom" "toggle-duration"
       "toggle-ease")
      ("animation" "doc" ,@animation) ("at-once" ,@animation) ("in-order" ,@animation)
      ("motif" "doc") ("variant" "doc") ("func" "doc") ("namespace" "doc") ("palette" "doc")))
  "Forms that take a body, and their keyword arguments. A keyword argument on a line of
its own is indented 4, like a positional argument, so it reads apart from the body at 2.")

(defconst mtp-mode--no-body
  '("circle" "rect" "ellipse" "line" "triangle" "polyline" "polygon" "arc" "ring" "text" "curve"
    "slider" "button" "play" "toggle" "readout" "on-drag" "on-click"
    "on-release" "on-dragend" "on-view" "on-enter" "on-leave" "on-pointermove"
    "move" "transition" "font" "color"
    "real" "int" "ratio" "complex" "bool" "string" "point" "list" "transform"
    "colormap" "interface" "defaults")
  "Forms that take no body: every item after their positional arguments is indented 4.")

(defconst mtp-mode--named
  '("scene" "group" "row" "column" "circle" "rect" "ellipse" "line" "triangle" "polyline" "polygon" "arc" "ring"
    "curve" "text" "font" "namespace" "palette" "interface" "colormap"
    "real" "int" "ratio" "complex" "bool" "string" "point" "list" "transform" "color"
    "type" "motif" "variant" "func" "transition" "animation"
    "canvas" "readout" "slider" "button" "play" "toggle")
  "Forms that take a name, so that (head_ …) has one argument fewer before its body.")

(defun mtp-mode--indent-function (indent-point state)
  "Indent an mtp form as Emacs Lisp indents a `defun'.
Positional and keyword arguments on lines of their own go 4 in from the
form's opening parenthesis, and every line of its body 2, whatever sits
on the head's line. A form with no body has only arguments. Forms mtp-mode does not know are indented as in Lisp, and a
list's items under its first item."
  (let* ((start (nth 1 state))
         (head (save-excursion
                 (goto-char (1+ start))
                 (buffer-substring-no-properties
                  (point) (progn (skip-syntax-forward "w_") (point)))))
         (unnamed (string-suffix-p "_" head))
         ;; line|none is a line, and circle_ a circle with no name.
         (base (car (split-string (if unnamed (substring head 0 -1) head) "|")))
         (count (cdr (assoc base mtp-mode--indent))))
    (cond
     ;; A list is data, not a call: its items line up under its first one.
     ((eq (char-after start) ?\[)
      (1+ (save-excursion (goto-char start) (current-column))))
     ;; A docstring reads with the body, whatever form it documents.
     ((save-excursion (goto-char indent-point) (skip-chars-forward " \t") (looking-at "doc@"))
      (+ 2 (save-excursion (goto-char start) (current-column))))
     ((not count)
      (lisp-indent-function indent-point state))
     (t
      ;; A form with no name: written head_, or, like an animation inside a control,
      ;; with a list where its name would be.
      (when (and (member base mtp-mode--named)
                 (or unnamed
                     (save-excursion
                       (goto-char (1+ start))
                       (forward-sexp 1)
                       (skip-chars-forward " \t\n")
                       (looking-at "[([]"))))
        (setq count (max 0 (1- count))))
      ;; (foreach ((i n) (j m)) …) has its bindings in one list, where (foreach i n …) has two.
      (when (and (equal base "foreach")
                 (save-excursion
                   (goto-char (1+ start))
                   (forward-sexp 1)
                   (skip-chars-forward " \t\n")
                   (looking-at "(")))
        (setq count 1))
      ;; How many of the form's arguments come before the line being indented.
      (let ((before 0))
        (save-excursion
          (goto-char (1+ start))
          (forward-sexp 1)
          (while (condition-case nil
                     (progn (forward-sexp 1) (< (point) indent-point))
                   (error nil))
            (setq before (1+ before))))
        (+ (save-excursion (goto-char start) (current-column))
           (if (or (< before count)
                   (member base mtp-mode--no-body)
                   (member (save-excursion
                             (goto-char indent-point)
                             (skip-chars-forward " \t")
                             (and (looking-at "(\\([^][() \t\n';]+\\)")
                                  (match-string-no-properties 1)))
                           (cdr (assoc base mtp-mode--keywords))))
               4 2)))))))

(defun mtp-mode--indent-line ()
  "Indent the line as `lisp-indent-line' does, but indent a comment like code.
mtp writes a comment on a line of its own with one ;, where Lisp would move it
to `comment-column'."
  (if (save-excursion (back-to-indentation) (looking-at ";"))
      (let ((indent (save-excursion (beginning-of-line) (calculate-lisp-indent)))
            (offset (- (current-column) (current-indentation))))
        (indent-line-to (if (consp indent) (car indent) (or indent 0)))
        (when (> offset 0) (move-to-column (+ (current-indentation) offset))))
    (lisp-indent-line)))

(defconst mtp-mode--font-lock
  `((,(concat "(\\(" (regexp-opt mtp-mode--heads) "\\)\\(?:|none\\)?_?\\_>")
     1 'mtp-mode-head-face)
    (,(concat "(\\(" (regexp-opt mtp-mode--arguments) "\\)\\_>") 1 font-lock-keyword-face)
    ("\\_<\\(doc\\)@'" 1 font-lock-keyword-face)
    (,(regexp-opt '("none" "true" "false" "self") 'symbols) . font-lock-constant-face))
  "What mtp-mode highlights: the heads of forms, keyword arguments, the doc of doc@'text', and
none, true, false and self.")

(defun mtp-mode--syntactic-face (state)
  "The face of the string or comment STATE is in: a docstring, the text of doc@'text', takes
`mtp-mode-doc-face'."
  (cond ((not (nth 3 state)) 'font-lock-comment-face)
        ((save-excursion
           (goto-char (nth 8 state))
           (looking-back "\\_<doc@" (max (point-min) (- (point) 4))))
         'mtp-mode-doc-face)
        (t 'font-lock-string-face)))

(defvar mtp-mode-syntax-table
  (let ((table (make-syntax-table lisp-data-mode-syntax-table)))
    ;; mtp strings are in single quotes, where Lisp would read ' as quote.
    (modify-syntax-entry ?' "\"" table)
    ;; | joins a type and none, as in line|none: part of a name, not a quote.
    (modify-syntax-entry ?| "_" table)
    ;; [ ] make lists and index them.
    (modify-syntax-entry ?\[ "(]" table)
    (modify-syntax-entry ?\] ")[" table)
    table)
  "Syntax table for mtp-mode.")

;;;###autoload
(define-derived-mode mtp-mode lisp-data-mode "mtp"
  "Major mode for mathterpiece .mtp files."
  :syntax-table mtp-mode-syntax-table
  (setq-local comment-start ";")
  (setq-local indent-tabs-mode nil)
  (setq-local lisp-indent-function #'mtp-mode--indent-function)
  (setq-local indent-line-function #'mtp-mode--indent-line)
  ;; Lisp's own region indenter moves one-; comments too, so indent line by line.
  (setq-local indent-region-function nil)
  (setq-local font-lock-defaults
              '(mtp-mode--font-lock nil nil nil nil
                (font-lock-syntactic-face-function . mtp-mode--syntactic-face))))

;;;###autoload
(add-to-list 'auto-mode-alist '("\\.mtp\\'" . mtp-mode))

(provide 'mtp-mode)
;;; mtp-mode.el ends here
