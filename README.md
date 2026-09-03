# FF / FB Behavioral Tasks (PsychoPy)

Feedforward / feedback (recurrent) processing に行動指標だけで迫るための **3つのPsychoPy課題**をまとめた実装です。

- Figure-ground segregation + backward masking
- Kanizsa illusory contour + backward masking
- Occluded object recognition + backward masking

> **重要**: 行動課題だけで FF/FB の神経結合方向そのものを直接測るわけではありません。ここで得られるのは、mask耐性・不完全刺激の補完・必要SOAなどを使った **behavioral proxy** です。

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py kanizsa
python main.py figure-ground
python main.py occluded-object
```

設定は `configs/default.json` にあります。実験前に少なくとも以下を確認してください。

- `monitor_hz`: 実際のディスプレイ刷新率
- `full_screen`: 本番は `true` 推奨
- participant / session
- 各課題のtrial数

## 1. Figure-ground + backward masking

中央領域だけ線分のorientationが背景と異なる `figure` 条件と、すべて同じorientationの `no-figure` 条件を提示します。直後にランダムorientationのmaskを出し、figureの有無を2AFCで回答します。

**代表的な行動指標**

- Accuracy
- d′
- masking cost（no-mask条件を追加した場合）

**解釈**

backward mask によって成績が選択的に落ちる程度を、figure-ground segregation に必要な recurrent / feedback processing への依存性の proxy として扱います。

Reference: Fahrenfort JJ, Scholte HS, Lamme VAF. *Masking disrupts reentrant processing in human visual cortex.* J Cogn Neurosci. 2007.

## 2. Kanizsa + backward masking

4つのPac-Man状inducerを短時間提示し、illusory contour (IC) / no contour (NC) を判定します。その後に可変SOAを置き、checker-like maskを提示します。

デフォルトでは 60 Hz を想定し、SOA候補は 17 / 67 / 117 / 167 ms です。コードは `monitor_hz` からフレーム数に丸め、実際に提示したフレーム数と実現SOAもCSVへ記録します。

**代表的な行動指標**

- SOAごとのAccuracy / d′
- psychometric curve
- 75% correct threshold (`T75`)

**解釈**

より短いSOAでもICを認識できるほど、feedback/recurrent completion が速い・頑健であるという proxy にします。

Reference: Freedman/Foxe/Knight et al. *The strength of feedback processing is associated with resistance to visual backward masking during illusory contour processing.* NeuroImage. 2022.

## 3. Occluded object + backward masking

物体を intact / partially occluded で提示し、maskあり/なしでカテゴリ分類を行います。

リポジトリは **著作権のある実験画像を同梱しません**。デフォルトでは circle / square / triangle / diamond の procedural demo stimuli で動作します。

本番で画像を使う場合は、権利を確認した画像を以下のように置いてください。

```text
stimuli/objects/
  cat/
    001.png
    002.png
  dog/
    001.png
  car/
    001.png
  chair/
    001.png
```

そして `configs/default.json` の `use_external_images` を `true` にします。最初の4カテゴリーが4AFCに使われます。

**代表的な行動指標**

- Accuracy / RT
- occlusion × mask の2×2または多水準効果
- recurrent benefit / masking cost

Reference: Wyatte D, Curran T, O’Reilly RC. *The limits of feedforward vision: recurrent processing promotes robust object recognition when objects are degraded.* J Cogn Neurosci. 2012.

## Analysis

```bash
python scripts/analyze.py data/sub-..._kanizsa_....csv
```

Kanizsaでは簡易logistic fitから75% thresholdを計算します。Figure-groundではd′、occluded objectではocclusion×maskごとのaccuracyを要約します。

## Timing / validation checklist

本番利用の前に必ず以下を確認してください。

1. PsychoPyのframe interval recordingでdroppingがないか
2. モニター刷新率を固定し、`monitor_hz` と一致させる
3. 17 ms刺激は60 Hzでは基本1 frame。120 Hz等では再設計する
4. maskの視角・コントラスト・SOAは先行研究に合わせてパイロット調整する
5. 被験者ごとにpsychometric curveが十分推定できるtrial数を確保する

## Scientific scope

この実装は、先行研究パラダイムの**再現・拡張をしやすい研究用ひな形**です。原著刺激を完全複製したものではありません。特に、刺激の視角、コントラスト、誘導子形状、mask特性、trial数は研究目的に合わせて原著Methodsを再確認してください。
