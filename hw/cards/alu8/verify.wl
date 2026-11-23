(* alu8 の桁上げ先見の配線の検証（Wolfram Language）。2026-11-23 に Wolfram の評価器で実行し、proof は 9 本とも True。
   74S181 の F・Cn+4 は sim/ic74/ic74181.py と同じ式（SDLS136 Table 2 で照合済み）、
   X（15 番）・Y（17 番）は論理図（SDLS136 5 頁）から写した式、74S182 の Cn+x は SDLS206 1 頁の式。
   つなぎ方は card.json の U1 X → U3 P0、U1 Y → U3 G0、U3 Cn+x → U2 Cn。
   比較先は 8bit に広げた 74181（spec）。変数は A0..7・B0..7・S0..S3・M・Cn（ピンのレベル、Cn は L で桁上げあり）。 *)
vars = Join[Array[a, 8, 0], Array[b, 8, 0], {s0, s1, s2, s3, m, cn}];
prop[i_] := a[i] || (s0 && b[i]) || (s1 && ! b[i]);
gen[i_] := a[i] && ((s3 && b[i]) || (s2 && ! b[i]));
alu181[k_, cnPin_] := Module[{p, g, c, gg, pp},
  p = Table[prop[k + i], {i, 0, 3}]; g = Table[gen[k + i], {i, 0, 3}];
  c = {! cnPin}; Do[AppendTo[c, g[[i]] || (p[[i]] && c[[i]])], {i, 4}];
  gg = g[[4]] || (p[[4]] && g[[3]]) || (p[[4]] && p[[3]] && g[[2]]) || (p[[4]] && p[[3]] && p[[2]] && g[[1]]);
  pp = And @@ p;
  <|"F" -> Table[Xor[p[[i]], g[[i]], ! m && c[[i]], m], {i, 4}],
    "Cn4" -> ! (gg || (pp && ! cnPin)),
    "X" -> Or @@ g,  (* 15 番: 上段 NOR（NOT gen）の 4 入力 NAND *)
    "Y" -> ! (! p[[4]] || (! g[[4]] && ! p[[3]]) || (! g[[4]] && ! g[[3]] && ! p[[2]]) ||
         (! g[[4]] && ! g[[3]] && ! g[[2]] && ! p[[1]]))|>];  (* 17 番: AND-OR-INVERT *)
cla182[cnPin_, g0Pin_, p0Pin_] := ! g0Pin || (! p0Pin && cnPin);  (* Cn+x = G0 + P0·Cn（G0・P0 はピンの反転） *)

lo = alu181[0, cn];
hi = alu181[4, cla182[cn, lo["Y"], lo["X"]]];
c8 = {! cn}; Do[AppendTo[c8, gen[i] || (prop[i] && c8[[i + 1]])], {i, 0, 7}];
specF = Table[Xor[prop[i], gen[i], ! m && c8[[i + 1]], m], {i, 0, 7}];
specCout = ! c8[[9]];

proof = Append[Table[TautologyQ[Equivalent[Join[lo["F"], hi["F"]][[i]], specF[[i]]], vars], {i, 8}],
   TautologyQ[Equivalent[hi["Cn4"], specCout], vars]];
(* 誤った配線（X と Y の入れ違い）は反例が出ること *)
swapped = alu181[4, cla182[cn, lo["X"], lo["Y"]]];
swapFails = SatisfiabilityInstances[! Equivalent[swapped["Cn4"], specCout], vars, 1] =!= {};
{"proof" -> proof, "swappedFails" -> swapFails}
