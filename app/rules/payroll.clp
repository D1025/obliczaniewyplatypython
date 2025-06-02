; Fakty wejściowe:
; (employee (id "123") (base-rate 6000))
; (overtime (fifty 10) (hundred 2))

(deftemplate employee
  (slot id) (slot base-rate))

(deftemplate overtime
  (slot fifty)   ; 50% godzin
  (slot hundred) ; 100% godzin
)

(deftemplate result
  (slot gross)          ; wynagrodzenie brutto
  (slot overtime-pay)   ; dodatek za nadgodziny
)

(defrule calc-overtime
  ?e <- (employee (base-rate ?base))
  ?o <- (overtime (fifty ?fifty) (hundred ?hundred))
=>
  (bind ?ot-pay (+ (* ?fifty (/ ?base 160) 1.5)
                   (* ?hundred (/ ?base 160) 2.0)))
  (assert (result (gross ?base)
                  (overtime-pay ?ot-pay))))
