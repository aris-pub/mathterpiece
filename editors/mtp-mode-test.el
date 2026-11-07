;;; mtp-mode-test.el --- Tests for mtp-mode -*- lexical-binding: t -*-
;; Run with: emacs --batch -l editors/mtp-mode.el -l editors/mtp-mode-test.el -f ert-run-tests-batch-and-exit

(require 'ert)
(require 'mtp-mode)

(defun mtp-mode-test--face-at (source word)
  "The face mtp-mode gives the first WORD in SOURCE."
  (with-temp-buffer
    (insert source)
    (mtp-mode)
    (font-lock-ensure)
    (goto-char (point-min))
    (search-forward word)
    (get-text-property (match-beginning 0) 'face)))

(ert-deftest mtp-mode-highlights-keyword-arguments ()
  (let ((src "(canvas view (x -8) (pan false)\n  pond)\n(on-view view (animation (move rise (to 0) (duration 0.8) (ease 'ease-out'))))"))
    (dolist (word '("x" "pan" "to 0" "duration" "ease"))
      (should (eq (mtp-mode-test--face-at src word) 'mtp-mode-keyword-face)))
    (should (eq (mtp-mode-test--face-at src "canvas") 'mtp-mode-form-head-face))
    (should (eq (mtp-mode-test--face-at src "animation") 'mtp-mode-form-head-face))))

(ert-deftest mtp-mode-highlights-shape-attributes ()
  (let ((src "(scene s (circle c (r 1) (fill teal) (stroke-width 2) (dash [4 2])))"))
    (dolist (word '("(r 1" "fill" "stroke-width" "dash"))
      (should (eq (mtp-mode-test--face-at src (string-trim-left word "(")) 'mtp-mode-keyword-face)))))

(ert-deftest mtp-mode-leaves-function-calls-alone ()
  (let ((src "(real v (sind (max 3 4)))"))
    (should-not (eq (mtp-mode-test--face-at src "sind") 'mtp-mode-keyword-face))
    (should-not (eq (mtp-mode-test--face-at src "max") 'mtp-mode-keyword-face))))

(ert-deftest mtp-mode-leaves-a-name-alone ()
  ;; (circle r …) names a circle r: r there is a name, not the attribute.
  (should-not (eq (mtp-mode-test--face-at "(circle fill (r 1))" "fill") 'mtp-mode-keyword-face)))

(ert-deftest mtp-mode-sets-a-docstring-apart ()
  (let ((src "(motif dot ((real r 1))\n  doc@'A dot.'\n  (circle c (r r) (fill 'red')))"))
    (should (eq (mtp-mode-test--face-at src "doc") 'mtp-mode-keyword-face))
    (should (eq (mtp-mode-test--face-at src "A dot") 'mtp-mode-doc-face))
    (should (eq (mtp-mode-test--face-at src "red") 'mtp-mode-string-face))))

(ert-deftest mtp-mode-indents-a-docstring-with-the-body ()
  (dolist (src '("(motif dot ((real r 1))\ndoc@'A dot.'\n(circle c (r r)))"
                 "(slider s (move k (from 0) (to 1))\ndoc@'Sets k.')"))
    (with-temp-buffer
      (insert src)
      (mtp-mode)
      (indent-region (point-min) (point-max))
      (goto-char (point-min))
      (search-forward "doc@")
      (should (= (current-indentation) 2)))))

(ert-deftest mtp-mode-sets-a-name-string-apart ()
  (let ((src "(scene s (circle #'dot-{k}' (fill 'red')))"))
    (should (eq (mtp-mode-test--face-at src "dot") 'mtp-mode-name-string-face))
    (should (eq (mtp-mode-test--face-at src "red") 'mtp-mode-string-face))))

(ert-deftest mtp-mode-reads-a-tex-string ()
  (let ((src "(formula f tex'\\frac{(a}{b} f\\'(x) \\\\' (term t (fill 'red')))"))
    (should (eq (mtp-mode-test--face-at src "tex") 'mtp-mode-keyword-face))
    (should (eq (mtp-mode-test--face-at src "frac") 'mtp-mode-string-face))
    (should (eq (mtp-mode-test--face-at src "red") 'mtp-mode-string-face))))

;;; mtp-mode-test.el ends here

(ert-deftest mtp-mode-highlights-declared-names ()
  (let ((src "(func[bool] done ((list[real] s)) (>= (part s 0) 1))\n(real k 1)\n(scene s (circle dot (r 1)))"))
    (should (eq (mtp-mode-test--face-at src "done") 'mtp-mode-function-name-face))
    (should (eq (mtp-mode-test--face-at src "k 1") 'mtp-mode-variable-name-face))
    (should (eq (mtp-mode-test--face-at src "dot") 'mtp-mode-variable-name-face))))

(ert-deftest mtp-mode-highlights-types-in-brackets ()
  (let ((src "(func[bool] done ((list[real] s)) s)"))
    (should (eq (mtp-mode-test--face-at src "bool") 'mtp-mode-type-face))
    (should (eq (mtp-mode-test--face-at src "real") 'mtp-mode-type-face))))

(ert-deftest mtp-mode-highlights-calls ()
  (let ((src "(real v (next (part s 0) (+ 1 2)))"))
    (dolist (word '("next" "part" "+ 1"))
      (should (eq (mtp-mode-test--face-at src word) 'mtp-mode-call-face)))))

(ert-deftest mtp-mode-highlights-what-let-binds ()
  (let ((src "(let ((i (part s 0)) (j 2)) (+ i j))"))
    (should (eq (mtp-mode-test--face-at src "i (") 'mtp-mode-variable-name-face))
    (should (eq (mtp-mode-test--face-at src "j 2") 'mtp-mode-variable-name-face))
    (should (eq (mtp-mode-test--face-at src "part") 'mtp-mode-call-face))))

(ert-deftest mtp-mode-highlights-numbers ()
  (should (eq (mtp-mode-test--face-at "(real k -12.5)" "-12.5") 'mtp-mode-number-face)))

(ert-deftest mtp-mode-highlights-nested-types-and-bindings-named-like-arguments ()
  (let ((src "(func[list[real]] step ((real s)) (let ((c 2)) c))"))
    (should (eq (mtp-mode-test--face-at src "real]") 'mtp-mode-type-face))
    (should (eq (mtp-mode-test--face-at src "c 2") 'mtp-mode-variable-name-face))))

(ert-deftest mtp-mode-sets-free-starts-apart ()
  ;; free@ declares a free value though an expression follows it, so it must stand out.
  (should (eq (mtp-mode-test--face-at "(real k free@(* 2 a))" "free@") 'mtp-mode-free-face)))

(ert-deftest mtp-mode-draws-nothing-in-italic ()
  ;; The author's rule: no italic. Every face the mode uses is its own, upright whatever the
  ;; theme's face it takes its color from.
  (let ((faces (seq-filter (lambda (f) (string-prefix-p "mtp-mode-" (symbol-name f))) (face-list))))
    (should (> (length faces) 5))
    (dolist (f faces) (should (eq (face-attribute f :slant) 'normal)))))

(ert-deftest mtp-mode-draws-heads-heavier-than-calls ()
  ;; Bold, which every font has: a weight the font lacks is drawn regular (seen 2026-11-07).
  (should (eq (face-attribute 'mtp-mode-form-head-face :weight) 'bold))
  (should (eq (face-attribute 'mtp-mode-call-face :weight) 'normal))
  (should (eq (mtp-mode-test--face-at "(real v (next 1))" "next") 'mtp-mode-call-face)))

(ert-deftest mtp-mode-reapplies-its-faces-when-loaded-again ()
  ;; defface leaves a face that exists as it is, so a reloaded mode kept old weights.
  (face-spec-set 'mtp-mode-form-head-face '((t :weight light)) 'face-defface-spec)
  (load (locate-library "mtp-mode") nil t)
  (should (eq (face-attribute 'mtp-mode-form-head-face :weight) 'bold)))
