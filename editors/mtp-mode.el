;;; mtp-mode.el --- Major mode for mathterpiece .mtp files -*- lexical-binding: t; -*-

;; Load it from your init file:
;;   (load "/path/to/mathterpiece/editors/mtp-mode.el")
;; Files ending in .mtp then open in mtp-mode.

;;; Code:

(require 'lisp-mode)

(defconst mtp-mode--heads
  '("scene" "group" "motif" "variant" "type" "func"
    "circle" "rect" "ellipse" "line" "triangle" "text"
    "real" "int" "ratio" "complex" "bool" "string" "point" "list" "transform"
    "color" "font"
    "transition" "move" "animation" "at-once" "in-order"
    "canvas" "readout" "slider" "button" "play" "toggle" "on-drag" "on-click"
    "repeat" "let" "fn" "if" "cond" "and" "or" "when" "else" "name" "as" "like")
  "Heads of mtp's forms. Any of them may end in an underscore, as in (circle_ …).")

(defconst mtp-mode--font-lock
  `((,(concat "(\\(" (regexp-opt mtp-mode--heads) "\\)\\(?:|none\\)?_?\\_>")
     1 font-lock-keyword-face)
    (,(regexp-opt '("none" "true" "false" "self") 'symbols) . font-lock-constant-face))
  "What mtp-mode highlights: the heads of forms, and none, true, false and self.")

(defvar mtp-mode-syntax-table
  (let ((table (make-syntax-table lisp-data-mode-syntax-table)))
    ;; mtp strings are in single quotes, where Lisp would read ' as quote.
    (modify-syntax-entry ?' "\"" table)
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
  (setq-local font-lock-defaults '(mtp-mode--font-lock)))

;;;###autoload
(add-to-list 'auto-mode-alist '("\\.mtp\\'" . mtp-mode))

(provide 'mtp-mode)
;;; mtp-mode.el ends here
