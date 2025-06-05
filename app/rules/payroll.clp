(defglobal
   ?*HOURS_FULL_TIME*      = 160
   ?*SOC_INS_EMP_PCT*      = 0.1371
   ?*HEALTH_INS_PCT*       = 0.09
   ?*PPK_EMP_PCT*          = 0.02
   ?*TAX_ADV_PCT_LO*       = 0.12
   ?*TAX_ADV_PCT_HI*       = 0.32
   ?*TAX_HI_THRESHOLD*     = 120000)

(deftemplate employee
   (slot first-name) (slot last-name)
   (slot contract-type) (slot is-student (default FALSE)))

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
   (slot private-km) (slot km-rate))

(deftemplate allowances
   (slot seniority-pct) (slot function-allow)
   (slot perf-bonus) (slot regulation-bonus)
   (slot night-allow) (slot weekend-allow)
   (slot remote-allow) (slot medical) (slot car))

(deftemplate deductions-pct
   (slot zus) (slot health) (slot ppk) (slot bail))

(deftemplate timesheet
   (slot hours-worked) (slot norm-hours (default ?*HOURS_FULL_TIME*)))

(deftemplate components
   (slot base-salary)
   (slot overtime-pay (default 0))
   (slot travel-pay  (default 0))
   (slot allow-pay   (default 0))
   (slot gross       (default 0)))

(deftemplate tax-advance (slot amount))

(deftemplate deductions
   (slot social  (default 0))
   (slot health  (default 0))
   (slot ppk     (default 0))
   (slot other   (default 0))
   (slot tax-adv (default 0)))

(deftemplate summary (slot net) (slot calc-date))

(defrule calc-base
  (position (base-rate ?rate) (fte ?fte))
  (timesheet (hours-worked ?hw) (norm-hours ?norm))
=>
  (bind ?base (* ?rate ?fte))
  (if (<> ?hw ?norm) then
      (bind ?base (* (/ ?hw ?norm) ?rate ?fte)))
  (assert (components (base-salary ?base))))

(defrule calc-overtime
  ?c <- (components (base-salary ?base))
  (overtime (fifty ?f) (hundred ?h) (mult50 ?m50) (mult100 ?m100))
  (timesheet (norm-hours ?norm))
=>
  (bind ?rate-hour (/ ?base ?norm))
  (bind ?pay (+ (* ?f ?rate-hour (- ?m50 1))
                (* ?h ?rate-hour (- ?m100 1))))
  (modify ?c (overtime-pay ?pay)))

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

(defrule calc-gross
  ?c <- (components (base-salary ?b)
                    (overtime-pay ?op)
                    (travel-pay  ?tp)
                    (allow-pay   ?ap))
=>
  (modify ?c (gross (+ ?b ?op ?tp ?ap))))

(defrule tax-adv-emp-work
  (employee (contract-type ?ct&:(or (eq ?ct UMOWA_O_PRACE) (eq ?ct DZIELO))))
  (components (gross ?g))
=>
  (bind ?low (* (min ?g ?*TAX_HI_THRESHOLD*) ?*TAX_ADV_PCT_LO*))
  (bind ?high (if (> ?g ?*TAX_HI_THRESHOLD*)
                 then (* (- ?g ?*TAX_HI_THRESHOLD*) ?*TAX_ADV_PCT_HI*)
                 else 0))
  (assert (tax-advance (amount (+ ?low ?high)))))

(defrule tax-adv-commission-student
  (employee (contract-type ZLECENIE) (is-student TRUE))
  (components)
=>
  (assert (tax-advance (amount 0))))

(defrule tax-adv-commission
  (employee (contract-type ZLECENIE) (is-student FALSE))
  (components (gross ?g))
=>
  (assert (tax-advance (amount (* ?g ?*TAX_ADV_PCT_LO*)))))

(defrule tax-adv-b2b
  (employee (contract-type B2B))
  (components)
=>
  (assert (tax-advance (amount 0))))

(defrule calc-deductions
  (components (gross ?gross))
  (deductions-pct (zus ?zusP) (health ?heaP)
                  (ppk ?ppkP) (bail ?bail))
  (tax-advance (amount ?taxAdv))
=>
  (bind ?zus     (* ?gross ?zusP))
  (bind ?health  (* ?gross ?heaP))
  (bind ?ppk     (* ?gross ?ppkP))
  (assert (deductions
            (social  ?zus)
            (health  ?health)
            (ppk     ?ppk)
            (other   ?bail)
            (tax-adv ?taxAdv))))

(defrule calc-net
  (components (gross ?gross))
  (deductions (social ?s) (health ?h) (ppk ?p) (other ?o) (tax-adv ?t))
=>
  (bind ?net (- ?gross ?s ?h ?p ?o ?t))
  (assert (summary (net ?net) (calc-date (gensym*)))))
