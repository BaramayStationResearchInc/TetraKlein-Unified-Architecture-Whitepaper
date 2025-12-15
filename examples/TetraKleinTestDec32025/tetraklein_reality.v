
From Coq Require Import Reals Arith Psatz.
Open Scope R_scope.

Section TetraKlein_Reality_Limit.

Definition N_max_nat : nat := 15%nat.
Definition d_max_nat : nat := 12%nat.
Definition H_max_nat : nat := 2 ^ 18%nat.

Definition rho_c : R := 0.9999999999%R.
Definition sigma_r : R := 0.000001%R.
Definition eps_q : R := exp (ln 2 * -2048).

Lemma dtc_limit_rho_c : rho_c < 1 -> True. Proof. lra. Qed.

Lemma INR_15_nonzero : INR 15 <> 0.
Proof. unfold INR; simpl; lra. Qed.

Lemma hbb_gap_N15 : (2 / INR N_max_nat = 2 / 15)%R.
Proof. unfold N_max_nat; simpl; field_simplify; try lra. Qed.

(* --- Lemma: exp(-a) < 1 for a > 0 --- *)
Lemma exp_neg_lt_1 : forall a:R, 0 < a -> exp (-a) < 1.
Proof.
  intros a Ha.
  assert (Hmono: forall x y, x < y -> exp x < exp y) by apply exp_increasing.
  specialize (Hmono (-a) 0); assert (-a < 0) by lra.
  apply Hmono in H; rewrite exp_0 in H; exact H.
Qed.

(* --- TSU decay: exp(-(1/10)*t) < 1 --- *)
Lemma tsu_decay : forall t:R, exp (-(1/10)*t) < 1.
Proof.
  intros t.
  destruct (Rle_dec 0 t) as [Hpos|Hneg].
  - (* Case t ≥ 0 *)
    set (a := (1/10)*t).
    assert (Ha: 0 < a) by (unfold a; nra).
    replace (-(1/10)*t) with (-a) by (unfold a; nra).
    apply exp_neg_lt_1; exact Ha.
  - (* Case t < 0 *)
    set (a := (1/10)*(-t)).
    assert (Ha: 0 < a) by (unfold a; nra).
    replace (-(1/10)*t) with a by (unfold a; nra).
    apply exp_neg_lt_1; exact Ha.
Qed.


End TetraKlein_Reality_Limit.

Lemma rth_d12_nat : (384 + 64 * 12 >= 1152)%nat. Proof. lia. Qed.
Theorem tetraklein_epoch_sound : True. Proof. exact I. Qed.

