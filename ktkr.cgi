#!/usr/local/bin/gosh

(use srfi-1)
(use file.util)
(use rfc.http)
(use rfc.uri)
(use gauche.process)
(use gauche.charconv)
(use text.html-lite)
(use util.match)
(use www.cgi)

;;inclusive.
(define (cut-file->string-list head file)
  (process-output->string-list (format #f "sed '1,~ad' ~a" head file)
			       :encoding 'SHIFT_JIS))

(define (read-last-modified file)
  (or (and-let* ((f (file->sexp-list file :if-does-not-exist #f))
		 ((not (null? f)))
		 (p (assoc "last-modified" (car f))))
	(cadr p))
      ""))

(define (get-2ch-dat-diff server board thread head)
  (let ((path (build-path "./dat2ch" server board thread)))
    (make-directory* path)
    (let ((orig-gz (build-path path "dat.gz"))
	  (file-h (build-path path "header"))
	  (orig (build-path path "orig"))
	  (diff (build-path path "diff"))
	  (sum (build-path path "dat")))      
      (cgi-add-temporary-file orig)
      (cgi-add-temporary-file diff)
      (cgi-add-temporary-file sum)
      (process-output->string (format #f "gzip -cdf ~a > ~a" orig-gz orig))
      (let ((orig-bytes (file-size orig))
	    (orig-lines (x->integer (string-scan (process-output->string `(wc -l ,orig)) #\space 'before))))
	(cut-file->string-list
	 head
	 (if (string=? "206" (call-with-output-file diff
			       (lambda (out)
				 (receive (status header body)
				     (http-get server (format #f "/~a/dat/~a.dat" board thread)
					       :user-agent "My Scheme Program/1.0"
					       :if-modified-since (read-last-modified file-h)
					       :range (format #f "bytes=~a-" orig-bytes)
					       :sink out
					       :flusher (lambda _ #t))
				   (call-with-output-file file-h (cut write header <>))
				   ;;debug
				   (format (current-error-port) "~a ~a\n" status header)
				   status))))
	   (begin
	     (process-output->string (format #f "cat ~a ~a > ~a && gzip -c ~a > ~a" orig diff sum sum orig-gz))
	     sum)
	   orig))))))

(define (get-2ch-datgz server board thread)
  (let ((path (build-path "./dat2ch" server board thread)))
    (make-directory* path)
    (let ((file (build-path path "dat.gz"))
	  (file-h (build-path path "header"))
	  (tmp (build-path path "tmp.gz")))
      (cgi-add-temporary-file tmp)
      (when (string=? "200" (call-with-output-file tmp
			      (lambda (out)
				(receive (status header body)
				    (http-get server (format #f "/~a/dat/~a.dat" board thread)
					      :user-agent "My Scheme Program/1.0"
					      :accept-encoding "gzip"
					      :if-modified-since (read-last-modified file-h)
					      :sink out
					      :flusher (lambda _ #t))
				  (call-with-output-file file-h (cut write header <>))
				  (format (current-error-port) "~a ~a\n" status header)
				  status))))
	(move-file tmp file :if-exists :supersede))
      (process-output->string-list `(gzip -cd ,file) :encoding 'SHIFT_JIS))))

(define (get-2ch-subjecttxt server board)
  (let ((path (build-path "./dat2ch" server board)))
    (make-directory* path)
    (let ((file (build-path path "subject.txt.gz"))
	  (tmp (build-path path "tmp.gz"))
	  (file-h (build-path path "header")))
      (cgi-add-temporary-file tmp)
      (when (string=? "200" (call-with-output-file tmp
			      (lambda (out)
				(receive (status header body)
				    (http-get server (format #f "/~a/subject.txt" board)
					      :user-agent "My Scheme Program/1.0"
					      :accept-encoding "gzip"
					      :if-modified-since (read-last-modified file-h)
					      :sink out
					      :flusher (lambda _ #t))
				  (call-with-output-file file-h (cut write header <>))
				  (format (current-error-port) "~a ~a\n" status header)
				  status))))
	(move-file tmp file :if-exists :supersede))
      (process-output->string-list `(gzip -cd ,file) :encoding 'SHIFT_JIS))))

(define (board-params-parse board)
  (and board (receive (scheme userinfo host port path query fragment) (uri-parse board)
	       (and-let* ((path (find (lambda (x)
					(not (zero? (string-length x))))
				      (string-split path #\/))))
		 (list host path)))))

(define (main args)
  (cgi-main
   (lambda (params)
     `(,(cgi-header)
       ,(match (list (board-params-parse (cgi-get-parameter "board" params))
		     (cgi-get-parameter "thread" params)
		     (cgi-get-parameter "head" params :convert x->number))
	       (((host path) #f #f) 
		(string-join (get-2ch-subjecttxt host path) "\n"))
	       (((host path) thread #f)
		(string-join (get-2ch-datgz host path thread) "\n"))
	       (((host path) thread head)
		(string-join (get-2ch-dat-diff host path thread head) "\n"))
	       (else
		`(,(html-doctype)
		  ,(html:html
		    (html:head)
		    (html:body
		     (html:table
		      :border 1
		      (html:tr (html:th "Name") (html:th "Value"))
		      (map (lambda (p)
			     (html:tr
			      (html:td (html-escape-string (car p)))
			      (html:td (html-escape-string (x->string (cdr p))))))
			   params)))))))))
   :on-error cgi-on-error/stack-trace))

(define (cgi-on-error/stack-trace e)
  `(,(cgi-header)
    ,(html-doctype)
    ,(html:html
      (html:head (html:title "Error"))
      (html:body (html:h1 "Error")
                 (html:pre (html-escape-string
                             (call-with-output-string
                               (cut
                                 with-error-to-port
                                 <>
                                 (cut report-error e)))))))))

;; Local variables:
;; mode: inferior-gauche
;; end:
