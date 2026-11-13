;;; mtp-mode.el --- Major mode for mathterpiece .mtp files -*- lexical-binding: t; -*-

;; Load it from your init file:
;;   (load "/path/to/mathterpiece/editors/mtp-mode.el")
;; Files ending in .mtp then open in mtp-mode.

;;; Code:

(require 'lisp-mode)

(defconst mtp-mode--heads
  '("scene" "group" "row" "column" "motif" "variant" "type" "func" "import" "choreo"
    "circle" "rect" "ellipse" "line" "triangle" "polyline" "polygon" "arc" "ring" "text" "curve"
    "real" "int" "ratio" "complex" "bool" "string" "point" "list" "transform"
    "color" "font" "namespace" "palette" "interface" "colormap" "formula" "term"
    "transition" "move" "wait" "roll-dice" "animation" "at-once" "in-order" "rand-seed"
    "canvas" "readout" "display" "slider" "button" "play" "stepper" "toggle" "on-drag" "on-click"
    "on-release" "on-dragstart" "on-dragend" "on-view" "on-enter" "on-leave" "on-pointermove"
    "on-rest" "on-live" "on-quiet" "defaults" "clip" "loop" "labels" "exists-when"
    "foreach" "let" "fn" "if" "cond" "and" "or" "when" "else" "name" "as" "like")
  "Heads of mtp's forms. Any of them may end in an underscore, as in (circle_ …).")

(defconst mtp-mode--arguments
  '("a" "active" "align" "b" "background" "buttons" "c" "clip" "controls" "dash" "dash-offset"
    "doc" "drawn" "duration" "ease" "family" "fill" "fill-opacity" "fixed-size" "font" "from" "gap"
    "halign" "height"
    "kind" "label" "like" "line-cap" "line-join" "num" "opacity" "outline" "outline-width" "padding" "pan" "path" "points"
    "in" "pointer-events" "pos" "r" "rest" "rounding" "rx"
    "ry" "seed" "size" "step" "stop-propagation" "stroke" "stroke-opacity" "stroke-width" "style" "tex" "to" "toggle-duration" "toggle-ease" "transform"
    "translate" "valign" "value" "weight" "width"
    "x" "y" "zoom")
  "Keyword arguments: the heads of the forms a form takes as its optional arguments,
such as (x -8), (duration 0.8) and (fill teal).")

;; Every face is the mode's own, upright, in the colors of Tango, the palette Emacs's tango
;; theme uses.

(defmacro mtp-mode--defface (face spec doc)
  "Declare FACE as defface does, then apply SPEC: defface leaves a face that exists as it is,
so loading the mode again would keep a face's old look."
  `(progn (defface ,face ,spec ,doc)
          (face-spec-set ',face ,spec 'face-defface-spec)))

(mtp-mode--defface mtp-mode-form-head-face
  '((t :foreground "#204a87" :weight bold :slant normal))
  "Face for the heads of mtp's forms, such as canvas in (canvas view …), in bold, the heaviest
weight every font has.")

(mtp-mode--defface mtp-mode-call-face
  '((t :foreground "#75507b" :weight normal :slant normal))
  "Face for the head of a function call, built in or the author's own, such as part in
(part s 0).")

(mtp-mode--defface mtp-mode-keyword-face
  '((t :foreground "#346604" :slant normal))
  "Face for keyword arguments, such as x in (x -8), and for doc@, tex' and (const).")

(mtp-mode--defface mtp-mode-function-name-face
  '((t :foreground "#a40000" :slant normal))
  "Face for the name a func, motif, variant, type or choreo declares.")

(mtp-mode--defface mtp-mode-variable-name-face
  '((t :foreground "#b35000" :slant normal))
  "Face for the name any other declaration declares, and for what let and foreach bind.")

(mtp-mode--defface mtp-mode-type-face
  '((t :foreground "#204a87" :slant normal))
  "Face for a type inside brackets, as real in list[real].")

(mtp-mode--defface mtp-mode-constant-face
  '((t :foreground "#5c3566" :slant normal))
  "Face for none, true, false and self.")

(mtp-mode--defface mtp-mode-number-face
  '((t :foreground "#ce5c00" :slant normal))
  "Face for numbers.")

(mtp-mode--defface mtp-mode-string-face
  '((t :foreground "#5c3566" :slant normal))
  "Face for strings.")

(mtp-mode--defface mtp-mode-comment-face
  '((t :foreground "#5f615c" :slant normal))
  "Face for comments.")

(mtp-mode--defface mtp-mode-doc-face
  '((t :foreground "#4e6a5a" :weight normal :slant normal))
  "Face for a docstring, the text of doc@'text': prose about the code, so a quiet gray-green,
apart from strings and comments. Themes often draw `font-lock-doc-face' faint, so it does not
inherit from it.")

(mtp-mode--defface mtp-mode-free-face
  '((t :foreground "#cc0000" :weight bold :slant normal))
  "Face for free@ in free@(f x): the value is free, starting at the expression's value and never
following it, though an expression is written there, so it is drawn to stand out.")

(mtp-mode--defface mtp-mode-name-string-face
  '((t :foreground "#a40000" :slant normal))
  "Face for a name string, #'dot-{k}', which is read as a name, not kept as a string, so it
takes a color apart from strings.")

(defconst mtp-mode--indent
  '(;; Forms with a name: the name, then their positional arguments, then their body.
    ("scene" . 1) ("group" . 1) ("row" . 1) ("column" . 1) ("circle" . 1) ("rect" . 1) ("ellipse" . 1) ("line" . 1)
    ("triangle" . 1) ("polyline" . 1) ("polygon" . 1) ("curve" . 1) ("arc" . 1) ("ring" . 1) ("text" . 2) ("font" . 1)
    ("namespace" . 1) ("palette" . 1) ("interface" . 1) ("colormap" . 2)
    ("formula" . 1) ("term" . 1) ("display" . 2)
    ("rand-seed" . 2) ("real" . 2) ("int" . 2) ("ratio" . 2) ("complex" . 2) ("bool" . 2) ("string" . 2)
    ("point" . 2) ("list" . 2) ("transform" . 2) ("color" . 2)
    ("type" . 2) ("motif" . 2) ("variant" . 2) ("func" . 2) ("choreo" . 2)
    ("transition" . 2) ("animation" . 1)
    ("canvas" . 1) ("readout" . 2) ("slider" . 2) ("button" . 1) ("play" . 1) ("stepper" . 1)
    ("toggle" . 2)
    ;; Forms with no name.
    ("move" . 1) ("at-once" . 0) ("in-order" . 0) ("step" . 1) ("on-drag" . 2) ("on-click" . 1)
    ("on-release" . 1) ("on-dragstart" . 1) ("on-dragend" . 1) ("on-view" . 0) ("on-enter" . 1)
    ("on-leave" . 1) ("on-rest" . 0) ("on-live" . 0) ("on-quiet" . 0)
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
      ("animation" "doc" ,@animation) ("choreo" "doc" ,@animation)
      ("at-once" ,@animation) ("in-order" ,@animation)
      ("motif" "doc") ("variant" "doc") ("func" "doc") ("namespace" "doc") ("palette" "doc")
      ("formula" "doc" "defaults")
      ("display" "doc" "kind") ("readout" "doc" "font")))
  "Forms that take a body, and their keyword arguments. A keyword argument on a line of
its own is indented 4, like a positional argument, so it reads apart from the body at 2.")

(defconst mtp-mode--no-body
  '("circle" "rect" "ellipse" "line" "triangle" "polyline" "polygon" "arc" "ring" "text" "curve"
    "slider" "button" "play" "stepper" "toggle" "on-drag" "on-click"
    "on-release" "on-dragstart" "on-dragend" "on-view" "on-enter" "on-leave" "on-pointermove"
    "on-rest" "on-live" "on-quiet" "move" "transition" "font" "color"
    "real" "int" "ratio" "complex" "bool" "string" "point" "list" "transform"
    "colormap" "interface" "defaults" "term" "rand-seed")
  "Forms that take no body: every item after their positional arguments is indented 4.")

(defconst mtp-mode--named
  '("scene" "group" "row" "column" "circle" "rect" "ellipse" "line" "triangle" "polyline" "polygon" "arc" "ring"
    "curve" "text" "font" "namespace" "palette" "interface" "colormap"
    "real" "int" "ratio" "complex" "bool" "string" "point" "list" "transform" "color"
    "type" "motif" "variant" "func" "choreo" "transition" "animation"
    "canvas" "readout" "slider" "button" "play" "stepper" "toggle" "formula" "display")
  "Forms that take a name, so that (head_ …) has one argument fewer before its body.")

(defun mtp-mode--skip-head ()
  "Move past the head that starts at point, with the type in brackets right after it.
[ ] are parentheses to Emacs, so without this func[real] would read as a head
and a list, as if the list stood where the name goes."
  (forward-sexp 1)
  (when (eq (char-after) ?\[)
    (forward-sexp 1)))

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
                       (mtp-mode--skip-head)
                       (skip-chars-forward " \t\n")
                       (looking-at "[([]"))))
        (setq count (max 0 (1- count))))
      ;; (foreach ((i n) (j m)) …) has its bindings in one list, where (foreach i n …) has two.
      (when (and (equal base "foreach")
                 (save-excursion
                   (goto-char (1+ start))
                   (mtp-mode--skip-head)
                   (skip-chars-forward " \t\n")
                   (looking-at "(")))
        (setq count 1))
      ;; How many of the form's arguments come before the line being indented.
      (let ((before 0))
        (save-excursion
          (goto-char (1+ start))
          (mtp-mode--skip-head)
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

(defconst mtp-mode--named-heads
  '("scene" "group" "row" "column" "circle" "rect" "ellipse" "line" "triangle" "polyline"
    "polygon" "arc" "ring" "text" "curve" "real" "int" "ratio" "complex" "bool" "string" "point"
    "list" "transform" "color" "font" "namespace" "palette" "interface" "colormap" "formula" "term"
    "transition" "animation" "canvas" "readout" "display" "slider" "button" "play" "stepper"
    "toggle" "rand-seed")
  "Heads whose form declares a name, the word after the head, as (circle dot …) declares dot.")

(defconst mtp-mode--types
  '("real" "int" "ratio" "complex" "bool" "string" "point" "list" "transform" "color" "font"
    "sequence" "func" "circle" "rect" "ellipse" "line" "triangle" "polyline" "polygon" "arc"
    "ring" "text" "curve" "group" "formula" "term" "transition")
  "Types, highlighted inside brackets, as real in list[real] and bool in func[bool].")

(defun mtp-mode--match-type (limit)
  "Find the next type inside the brackets of a type, as real in list[real] or func[real real],
before LIMIT."
  (let ((re (concat "\\_<\\(" (regexp-opt mtp-mode--types) "\\)\\_>"))
        found)
    (while (and (not found) (re-search-forward re limit t))
      (let ((open (nth 1 (save-match-data (save-excursion (syntax-ppss (match-beginning 0)))))))
        (when (and open
                   (eq (char-after open) ?\[)
                   (> open (point-min))
                   (memq (char-syntax (char-before open)) '(?w ?_)))
          (setq found t))))
    found))

(defun mtp-mode--match-binding (limit)
  "Find the next name a let or a foreach binds, as i in (let ((i 1)) …), before LIMIT."
  (let (found)
    (while (and (not found)
                (re-search-forward "(\\(\\(?:\\sw\\|\\s_\\)+\\)" limit t))
      (let ((outer (nth 1 (save-excursion (syntax-ppss (match-beginning 0))))))
        (when (and outer
                   (save-match-data
                     (save-excursion
                       (goto-char outer)
                       (looking-back "(\\(?:let\\|foreach\\)[ \t\n]+"
                                     (max (point-min) (- (point) 20))))))
          (setq found t))))
    found))

(defun mtp-mode--match-call (limit)
  "Find the next head of a form that is a function call, before LIMIT: every head that is
not one of mtp's forms or keyword arguments, which earlier rules have already highlighted."
  (let (found)
    (while (and (not found)
                (re-search-forward "(\\([^][() \t\n';\"#@]+\\)" limit t))
      (unless (or (save-match-data (let ((st (syntax-ppss))) (or (nth 3 st) (nth 4 st))))
                  (get-text-property (match-beginning 1) 'face))
        (setq found t)))
    found))

(defconst mtp-mode--font-lock
  `((,(concat "(\\(" (regexp-opt mtp-mode--heads) "\\)\\(?:|none\\)?_?\\_>")
     1 'mtp-mode-form-head-face)
    (,(concat "(\\(?:func\\|motif\\|variant\\|type\\|choreo\\)\\(?:\\[[^ \t\n()]*\\]\\)?[ \t]+"
              "\\([^][() \t\n';\"#]+\\)")
     1 'mtp-mode-function-name-face)
    (,(concat "(" (regexp-opt mtp-mode--named-heads) "\\(?:\\[[^ \t\n()]*\\]\\)?\\(?:|none\\)?[ \t]+"
              "\\([^][() \t\n';\"#0-9-][^][() \t\n';\"#]*\\)")
     1 'mtp-mode-variable-name-face)
    (mtp-mode--match-type 1 'mtp-mode-type-face)
    (mtp-mode--match-binding 1 'mtp-mode-variable-name-face)
    (,(concat "(\\(" (regexp-opt mtp-mode--arguments) "\\)\\_>") 1 'mtp-mode-keyword-face)
    ("(\\(const\\))" 1 'mtp-mode-keyword-face)
    ("\\_<\\(doc\\)@'" 1 'mtp-mode-keyword-face)
    ("\\_<\\(tex\\)'" 1 'mtp-mode-keyword-face)
    ("\\_<\\(free@\\)" 1 'mtp-mode-free-face)
    (,(regexp-opt '("none" "true" "false" "self") 'symbols) . 'mtp-mode-constant-face)
    ("\\_<-?[0-9]+\\(?:\\.[0-9]*\\)?\\_>" . 'mtp-mode-number-face)
    (mtp-mode--match-call 1 'mtp-mode-call-face))
  "What mtp-mode highlights: the heads of forms, the names they declare, types in brackets,
keyword arguments, the doc of doc@'text', the tex of tex'LaTeX', free@, none, true, false and self,
numbers, the names let and foreach bind, and function calls.")

(defun mtp-mode--syntactic-face (state)
  "The face of the string or comment STATE is in: a docstring, the text of doc@'text', takes
`mtp-mode-doc-face'."
  (cond ((not (nth 3 state)) 'mtp-mode-comment-face)
        ((save-excursion
           (goto-char (nth 8 state))
           (looking-back "\\_<doc@" (max (point-min) (- (point) 4))))
         'mtp-mode-doc-face)
        ((eq (char-before (nth 8 state)) ?#) 'mtp-mode-name-string-face)
        (t 'mtp-mode-string-face)))

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
