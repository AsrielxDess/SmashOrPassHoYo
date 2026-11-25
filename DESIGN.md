---
# gstack: design-md-format=spec
name: Smash or Pass — Salle des vœux
description: Une scène sombre d'écran de tirage où chaque perso est révélée comme un tirage gacha ; le site change de peau selon le jeu.
colors:
  genshin-bg: "#0E1424"
  genshin-surface: "#18213A"
  genshin-line: "#2A3553"
  genshin-text: "#F2EADB"
  genshin-muted: "#8E97AC"
  genshin-accent: "#CFA867"
  zzz-bg: "#121212"
  zzz-surface: "#1E1E1B"
  zzz-line: "#34342F"
  zzz-text: "#F1EFE6"
  zzz-muted: "#8B8A82"
  zzz-accent: "#F2D40C"
  smash: "#1FAF6E"
  pass: "#D8423B"
typography:
  display-genshin:
    fontFamily: Marcellus
    fontWeight: 400
    fontSize: clamp(40px, 5.4vw, 84px)
    letterSpacing: 0.06em
  display-zzz:
    fontFamily: Anton
    fontWeight: 400
    fontSize: clamp(40px, 5.4vw, 84px)
    letterSpacing: 0.01em
  body:
    fontFamily: Satoshi
    fontSize: 1rem
    lineHeight: 1.5
  label:
    fontFamily: Satoshi
    fontSize: 0.8125rem
    letterSpacing: 0.18em
rounded:
  genshin: 3px
  zzz: 0px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
components:
  button-smash:
    backgroundColor: "{colors.smash}"
    textColor: "#FFFFFF"
  button-pass:
    backgroundColor: "{colors.pass}"
    textColor: "#FFFFFF"
---

# Smash or Pass — Salle des vœux

## Overview

**Creative North Star:** l'écran de tirage d'un gacha, où la perso apparaît comme une récompense. Le fond reste sombre pour que les modèles 3D et les splash arts en couleur soient la seule source d'éclat.
**Product context:** jeu de fan local, un seul `index.html`, pour Genshin Impact et Zenless Zone Zero, joué seul ou entre potes sur PC le soir.
**Mode per surface:** Accueil = Persuade · Vote = Experience · Entre-rounds, classement et pyramide = Operate.
**Reference sites:** genshin.hoyoverse.com/fr/character (grand nom en serif, losanges ◇, filets dorés, perso qui déborde).
**Key characteristics:** des perso sans cadre posées sur une scène · un grand nom gravé · un vote qui claque comme un tampon · un site qui change de peau entre les deux jeux.

## Colors

**Strategy:** Restrained. Une seule couleur d'accent par jeu (or pour Genshin, jaune signal pour ZZZ). Vert et rouge sont réservés au vote : SMASH en vert, PASS en rouge, comme dans la demande de départ.
**Light or dark:** sombre, parce que le jeu se joue le soir à l'écran et que les personnages doivent porter toute la couleur. Le bleu nuit de Genshin évite le violet ; l'asphalte de ZZZ est neutre et légèrement chaud.

## Typography

- **Genshin :** Marcellus (Google Fonts), des capitales à empattements évasés qui évoquent les inscriptions gravées de Teyvat sans copier le logo officiel.
- **ZZZ :** Anton (Google Fonts), condensé et très gras, dans l'esprit des affiches de rue de New Eridu.
- **Texte et interface :** Satoshi (Fontshare), lisible et neutre, dans les deux thèmes.
- **Échelle :** le nom de la perso domine (40 à 84 px). Les chiffres de round s'écrivent dans la police display, sans police mono.

## Layout

- **Vote, bureau :** grille 34 % / 66 %. À gauche, la région, le nom, le filet et les boutons, alignés en bas. À droite, la scène.
- **Vote, mobile (< 860 px) :** nom en haut, scène au milieu, boutons en bas.
- **Accueil :** deux portails plein écran ; celui survolé s'élargit.
- **Pyramide :** centrée. Les rangées d'éliminées sont en éventail, avec un chevauchement de 18 px.

## Elevation & Depth

La profondeur vient d'ombres décalées et opaques (`0 6px 0`) sous les boutons et les vignettes, et d'une ombre de sol floue sous la perso. Pas de halo coloré, pas de lueur.

## Shapes

Genshin a des angles presque vifs (3 px) et des losanges ◇ comme ornements. ZZZ a des angles droits, des boutons inclinés de -8° (`skewX`) et des bandes de chantier.

## Components

- **Boutons de vote :** pleins, ombre décalée, et enfoncement de 4 px au clic ou à la touche.
- **Sélecteurs (3D/Image, Idle/Marche) :** segments ; l'option active prend la couleur d'accent.
- **Vignettes :** format portrait 2:3, avec le nom en surimpression.
- **Focus clavier :** contour visible de 2 px en couleur d'accent.

## Do's and Don'ts

- Do : laisser la perso sans cadre ; le fond de scène reste un simple motif de filets.
- Do : garder une seule couleur d'accent par thème.
- Do : réserver le vert et le rouge au vote.
- Don't : dégradé violet, halo lumineux, texte en dégradé.
- Don't : cartes dans des cartes, ou un rayon d'arrondi identique partout.
- Don't : utiliser le logo ou les polices officielles des jeux.

## Motion

- **Approach :** intentional.
- **Easing :** cubic-bezier(.2,.8,.2,1) en sortie.
- **Durées :** tampon 140 ms, sortie de la perso 320 ms, rideau 550 ms, élargissement d'un portail 600 ms.
- **Le moment signé :** la révélation. Pour Genshin, un rideau à deux battants bordés d'or s'ouvre ; pour ZZZ, une bande jaune balaie la scène. Ensuite, le vote claque un tampon SMASH ou PASS sur la perso. Tout s'arrête avec `prefers-reduced-motion`.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-11-25 | Système de design initial | /design-consultation : brief « écran de gacha premium », recherche sur le site officiel de Genshin, avis indépendant d'un sous-agent (idées reprises : le tampon et l'éventail de cartes) |
