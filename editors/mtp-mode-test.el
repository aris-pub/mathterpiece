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
  (let ((src "(canvas view (view-x -8) (pan false)\n  pond)\n(on-view view (animation (move rise (to 0) (duration 0.8) (ease 'ease-out'))))"))
    (dolist (word '("view-x" "pan" "to 0" "duration" "ease"))
      (should (eq (mtp-mode-test--face-at src word) 'font-lock-keyword-face)))
    (should (eq (mtp-mode-test--face-at src "canvas") 'mtp-mode-head-face))
    (should (eq (mtp-mode-test--face-at src "animation") 'mtp-mode-head-face))))

(ert-deftest mtp-mode-highlights-shape-attributes ()
  (let ((src "(scene s (circle c (r 1) (fill teal) (stroke-width 2) (dash [4 2])))"))
    (dolist (word '("(r 1" "fill" "stroke-width" "dash"))
      (should (eq (mtp-mode-test--face-at src (string-trim-left word "(")) 'font-lock-keyword-face)))))

(ert-deftest mtp-mode-leaves-function-calls-alone ()
  (let ((src "(real v (sind (max 3 4)))"))
    (should-not (eq (mtp-mode-test--face-at src "sind") 'font-lock-keyword-face))
    (should-not (eq (mtp-mode-test--face-at src "max") 'font-lock-keyword-face))))

(ert-deftest mtp-mode-leaves-a-name-alone ()
  ;; (circle r …) names a circle r: r there is a name, not the attribute.
  (should-not (eq (mtp-mode-test--face-at "(circle fill (r 1))" "fill") 'font-lock-keyword-face)))

;;; mtp-mode-test.el ends here
