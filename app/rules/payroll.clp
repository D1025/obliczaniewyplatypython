;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;  payroll.clp  (wersja zweryfikowana – brak nadmiarowych ")")
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defglobal
   ?*HOURS_FULL_TIME*      = 160
   ?*SOC_INS_EMP_PCT*      = 0.1371
   ?*HEALTH_INS_PCT*       = 0.09
   ?*PPK_EMP_PCT*          = 0.02
   ?*TAX_ADV_PCT_LO*       = 0.12
   ?*TAX_ADV_PCT_HI*       = 0.32
   ?*TAX_HI_THRESHOLD*     = 120000)

;--------------------------------------------------------------------
;  INPUT TEMPLATES
;--------------------------------------------------------------------

(deftemplate employee
   (slot first-name) (slot last-name) (slot contract-type))

(deftemplate position
   (slot base-rate) (slot currency) (slot fte (default 1.0)))

(deftemplate period (slot start) (slot end))

(deftemplate overtime
   (slot fifty) (slot hundred) (slot night (default 0))
   (slot mult50  (default 1.5))
   (slot mult100 (default 2.0)))

(deftemplate travel
   (slot dom-days) (slot abrd-days)
   (slot dom-rate) (slot abrd-rate)
   (slot accomodation) (slot lump-sum)
   (slot private-km)   (slot km-rate))

(deftemplate allowances
   (slot seniority-pct)  (slot function-allow)
   (slot perf-bonus)     (slot regulation-bonus)
   (slot night-allow)    (slot weekend-allow)
   (slot remote-allow)   (slot medical) (slot car))

(deftemplate deductions-pct
   (slot zus) (slot health) (slot tax-adv)
   (slot ppk) (slot bail))

(deftemplate timesheet
   (slot hours-worked)
   (slot norm-hours (default ?*HOURS_FULL_TIME*)))

;--------------------------------------------------------------------
;  OUTPUT TEMPLATES
;--------------------------------------------------------------------

(deftemplate components
   (slot base-salary)
   (slot overtime-pay (default 0))
   (slot travel-pay  (default 0))
   (slot allow-pay   (default 0))
   (slot gross       (default 0)))

(deftemplate deductions
   (slot social  (default 0))
   (slot health  (default 0))
   (slot ppk     (default 0))
   (slot other   (default 0))
   (slot tax-adv (default 0)))

(deftemplate summary
   (slot net) (slot calc-date))

;--------------------------------------------------------------------
;  RULES
;--------------------------------------------------------------------

; 1️⃣  Base salary
(defrule calc-base
  (position (base-rate ?rate) (fte ?fte))
  (timesheet (hours-worked ?hw) (norm-hours ?norm))
=>
  (bind ?base (* ?rate ?fte))
  (if (<> ?hw ?norm) then
      (bind ?base (* (/ ?hw ?norm) ?rate ?fte)))
  (assert (components (base-salary ?base))))

; 2️⃣  Overtime
(defrule calc-overtime
  ?c <- (components (base-salary ?base))
  (overtime (fifty ?f) (hundred ?h) (mult50 ?m50) (mult100 ?m100))
  (timesheet (norm-hours ?norm))
=>
  (bind ?rate-hour (/ ?base ?norm))
  (bind ?pay (+ (* ?f ?rate-hour (- ?m50 1))
                (* ?h ?rate-hour (- ?m100 1))))
  (modify ?c (overtime-pay ?pay)))

; 3️⃣  Travel allowances
(defrule calc-travel
  ?c <- (components)
  (travel (dom-days ?dd) (abrd-days ?ad)
          (dom-rate ?dr) (abrd-rate ?ar)
          (accomodation ?acc) (lump-sum ?ls)
          (private-km ?km) (km-rate ?kr))
=>
  (bind ?diet (+ (* ?dd ?dr) (* ?ad ?ar)))
  (bind ?kmPay (* ?km ?kr))
  (bind ?total (+ ?diet ?acc ?ls ?kmPay))
  (modify ?c (travel-pay ?total)))

; 4️⃣  Other allowances & bonuses
(defrule calc-allowances
  ?c <- (components (base-salary ?base))
  (allowances (seniority-pct ?sen)
              (function-allow ?func)
              (perf-bonus ?perf)
              (regulation-bonus ?reg)
              (night-allow ?na)
              (weekend-allow ?wa)
              (remote-allow ?ra)
              (medical ?med)
              (car ?car))
=>
  (bind ?senior (* ?base ?sen))
  (bind ?sum (+ ?senior ?func ?perf ?reg ?na ?wa ?ra ?med ?car))
  (modify ?c (allow-pay ?sum)))

; 5️⃣  Gross
(defrule calc-gross
  ?c <- (components (base-salary ?b)
                    (overtime-pay ?op)
                    (travel-pay  ?tp)
                    (allow-pay   ?ap))
=>
  (modify ?c (gross (+ ?b ?op ?tp ?ap))))

; 6️⃣  Percentage deductions
(defrule calc-deductions
  (components (gross ?gross))
  (deductions-pct (zus ?zusP) (health ?heaP)
                  (ppk ?ppkP) (tax-adv ?taxP)
                  (bail ?bail))
=>
  (bind ?zus     (* ?gross ?zusP))
  (bind ?health  (* ?gross ?heaP))
  (bind ?ppk     (* ?gross ?ppkP))
  (bind ?taxAdv  (* ?gross ?taxP))  ; uproszczenie
  (assert (deductions
            (social  ?zus)
            (health  ?health)
            (ppk     ?ppk)
            (other   ?bail)
            (tax-adv ?taxAdv))))

; 7️⃣  Net
(defrule calc-net
  (components (gross ?gross))
  (deductions (social ?s) (health ?h) (ppk ?p) (other ?o) (tax-adv ?t))
=>
  (bind ?net (- ?gross ?s ?h ?p ?o ?t))
  (assert (summary (net ?net) (calc-date (gensym*))))
)
