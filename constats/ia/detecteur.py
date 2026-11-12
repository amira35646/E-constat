import io
from pathlib import Path

import joblib
import torch
import torch.nn as nn
import torchvision
from PIL import Image, ImageOps
from torchvision import transforms as T
from transformers import CLIPModel, CLIPProcessor

DOSSIER = Path(__file__).parent / "modeles"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DTYPE = torch.float16 if DEVICE.type == "cuda" else torch.float32

SEUIL_BAS, SEUIL_HAUT = 0.35, 0.65

SUJETS = ["a photo of a car", "a photo of a damaged car",
          "a close-up photo of a car body panel", "a photo of a person",
          "a photo of an animal", "a photo of a landscape", "a photo of a building",
          "a photo of food", "a photo of a document or screenshot", "a photo of an object"]

_etat = {}  # les modèles sont chargés une seule fois


def _vecteur(sortie):
    if not torch.is_tensor(sortie):
        sortie = sortie.pooler_output
    return sortie / sortie.norm(dim=-1, keepdim=True)


def _charger():
    if _etat:
        return _etat
    sauvegarde = joblib.load(DOSSIER / "detecteur_v2.joblib")
    nom_clip = sauvegarde["clip"]

    clip = CLIPModel.from_pretrained(nom_clip, torch_dtype=DTYPE).to(DEVICE).eval()
    processeur = CLIPProcessor.from_pretrained(nom_clip)

    resnet = torchvision.models.resnet50(weights=None)
    resnet.fc = nn.Linear(resnet.fc.in_features, 1)
    resnet.load_state_dict(torch.load(DOSSIER / "resnet_v2.pth", map_location="cpu"))
    resnet = resnet.to(DEVICE).eval()

    with torch.no_grad():
        entree = processeur(text=SUJETS, return_tensors="pt", padding=True).to(DEVICE)
        vec_sujets = _vecteur(clip.get_text_features(**entree)).float()

    _etat.update(
        clf=sauvegarde["classifieur"], clip=clip, processeur=processeur,
        resnet=resnet, vec_sujets=vec_sujets,
        normaliser=T.Compose([T.ToTensor(),
                              T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]),
    )
    return _etat


def _preparer(chemin):
    """Même préparation qu'à l'entraînement : carré, 224x224, JPEG qualité 90."""
    img = ImageOps.exif_transpose(Image.open(chemin)).convert("RGB")
    w, h = img.size
    c = min(w, h)
    g, t = (w - c) // 2, (h - c) // 2
    img = img.crop((g, t, g + c, t + c)).resize((224, 224), Image.LANCZOS)
    tampon = io.BytesIO()
    img.save(tampon, "JPEG", quality=90)
    return Image.open(io.BytesIO(tampon.getvalue())).convert("RGB")


def analyser(chemin_image):
    """Renvoie : verdict, score, p_clip, p_resnet, p_voiture."""
    e = _charger()
    img = _preparer(chemin_image)

    with torch.no_grad():
        x = e["processeur"](images=[img], return_tensors="pt")["pixel_values"].to(DEVICE, DTYPE)
        v = _vecteur(e["clip"].get_image_features(pixel_values=x)).float()

        sims = (100 * v @ e["vec_sujets"].T).softmax(dim=-1)[0].cpu().numpy()
        p_voiture = float(sims[0] + sims[1] + sims[2])

        p_clip = float(e["clf"].predict_proba(v.cpu().numpy())[0, 1])

        xr = e["normaliser"](img)[None].to(DEVICE)
        p_resnet = float(torch.sigmoid(e["resnet"](xr).float())[0, 0])

    p = (p_clip + p_resnet) / 2

    if p_voiture < 0.5:
        verdict = "non_voiture"
    elif p >= SEUIL_HAUT:
        verdict = "authentique"
    elif p <= SEUIL_BAS:
        verdict = "suspecte"
    else:
        verdict = "incertain"

    return {"verdict": verdict, "score": p, "p_clip": p_clip,
            "p_resnet": p_resnet, "p_voiture": p_voiture}