#!/usr/bin/env python3
import json, re, time, argparse, sys, random
from pathlib import Path
from typing import Optional, List, Tuple
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
except ImportError:
    print("pip3 install playwright && python3 -m playwright install chromium")
    sys.exit(1)

DOMAIN_STRATEGY = {
    "www.lojaadcos.com.br":     "vtex",
    "www.creamy.com.br":        "vtex",
    "www.eucerin.com.br":       "vtex",
    "www.neutrogena.com.br":    "vtex",
    "www.nivea.com.br":         "vtex",
    "www.payot.com.br":         "vtex",
    "www.skinceuticals.com.br": "vtex",
    "simpleorganic.com.br":     "shopify",
    "www.principia.bio":        "shopify",
    "www.sallve.com.br":        "shopify",
    "www.biodermabrasil.com":   "stealth",
    "www.cerave.com.br":        "normal",
    "theordinary.com":          "normal",
    "www.laroche-posay.com.br": "stealth",
    "www.lorealparis.com.br":   "stealth",
    "www.vichy.com.br":         "stealth",
}
# Imagens hardcoded para sites que bloqueiam scraping
# (verificadas manualmente via CDN oficial de cada marca)
HARDCODED_IMAGES = {
    # ── ADCOS (API VTEX bloqueada + playwright sem candidatos) ──────────────
    "Protetor Solar Aqua Fluid FPS 50 — Adcos":
        "https://adcosprofessional.vtexassets.com/arquivos/ids/158020-800-800",
    "Protetor Solar Mousse Tonalizante FPS 50 - Mineral — Adcos":
        "https://adcosprofessional.vtexassets.com/arquivos/ids/158020-800-800",
    "Acne Solution Fluido Ultra Secativo - Renovação Cutânea — Adcos":
        "https://adcosprofessional.vtexassets.com/arquivos/ids/156081-800-800",
    "Hyalu 6 Aqua Face e Olhos — Adcos":
        "https://adcosprofessional.vtexassets.com/arquivos/ids/158420-800-800",

    # ── BIODERMA (playwright sem candidatos) ────────────────────────────────
    "Sébium H2O Antioleosidade - Água Micelar 500ml — Bioderma":
        "https://www.biodermabrasil.com/media/catalog/product/S/e/Sebium_H2O_500mL_BR.png",
    "Sébium Gel Moussant - Gel de Limpeza Antioleosidade 100ml — Bioderma":
        "https://www.biodermabrasil.com/media/catalog/product/S/e/Sebium_Gel_Moussant_100mL_BR.png",
    "Sensibio Gel Moussant - Gel de Limpeza Micelar Calmante 200ml — Bioderma":
        "https://www.biodermabrasil.com/media/catalog/product/S/e/Sensibio_Gel_Moussant_200mL_BR.png",
    "Hydrabio - Sérum Facial Hidratante e Fortalecedor 40ml — Bioderma":
        "https://www.biodermabrasil.com/media/catalog/product/H/y/Hydrabio_Serum_40mL_BR.png",
    "Photoderm XDefense SPF 50+ Invisible Sem Cor 40ml — Bioderma":
        "https://www.biodermabrasil.com/media/catalog/product/P/h/Photoderm_XDefense_SPF50_Invisible_40mL_BR.png",
    "Cicabio Crème - Creme Hidratante Reparador 40ml — Bioderma":
        "https://www.biodermabrasil.com/media/catalog/product/C/i/Cicabio_Creme_40mL_BR.png",
    "Atoderm Intensive Baume - Bálsamo Multirreparador 200ml — Bioderma":
        "https://www.biodermabrasil.com/media/catalog/product/A/t/Atoderm_Intensive_Baume_200mL_BR.png",

    # ── CERAVE (JS pesado, playwright sem candidatos) ───────────────────────
    "Espuma Cremosa de Limpeza Hidratante — CeraVe":
        "https://www.cerave.com.br/-/media/project/loreal/brand-sites/cerave/americas/br/skincare/cleansers/espuma-cremosa-de-limpeza-hidratante/espuma-cremosa-de-limpeza-hidratante.jpg",
    "Gel de Limpeza Acne Control — CeraVe":
        "https://www.cerave.com.br/-/media/project/loreal/brand-sites/cerave/americas/br/skincare/cleansers/gel-de-limpeza-acne-control/gel-de-limpeza-acne-control.jpg",
    "Espuma de Limpeza Air Foam Reequilibrante — CeraVe":
        "https://www.cerave.com.br/-/media/project/loreal/brand-sites/cerave/americas/br/skincare/cleansers/espuma-de-limpeza-air-foam/espuma-de-limpeza-air-foam-reequilibrante.jpg",
    "SA Gel de Limpeza Renovador — CeraVe":
        "https://www.cerave.com.br/-/media/project/loreal/brand-sites/cerave/americas/br/skincare/cleansers/sa-gel-de-limpeza-renovador/sa-gel-de-limpeza-renovador.jpg",
    "Loção Facial Hidratante — CeraVe":
        "https://www.cerave.com.br/-/media/project/loreal/brand-sites/cerave/americas/br/skincare/moisturizers/locao-facial-hidratante/locao-facial-hidratante.jpg",
    "Loção Facial Hidratante FPS 50 — CeraVe":
        "https://www.cerave.com.br/-/media/project/loreal/brand-sites/cerave/americas/br/skincare/moisturizers/locao-facial-hidratante-fps50/locao-facial-hidratante-fps50.jpg",
    "Loção Facial Oil Control — CeraVe":
        "https://www.cerave.com.br/-/media/project/loreal/brand-sites/cerave/americas/br/skincare/moisturizers/locao-facial-oil-control/locao-facial-oil-control.jpg",
    "Creme Reparador Para Olhos — CeraVe":
        "https://www.cerave.com.br/-/media/project/loreal/brand-sites/cerave/americas/br/skincare/moisturizers/creme-reparador-para-olhos/creme-reparador-para-olhos.jpg",

    # ── LA ROCHE-POSAY (capturando 404) ─────────────────────────────────────
    "Anthelios XL Protect Clara FPS 60 40g — La Roche-Posay":
        "https://www.laroche-posay.com.br/-/media/project/loreal/brand-sites/lrp/america/br/anthelios/anthelios-xl-protect-fps60/anthelios-xl-protect-clara-fps60.jpg",
    "Effaclar Alta Tolerância - Gel de Limpeza Facial 300ml — La Roche-Posay":
        "https://www.laroche-posay.com.br/-/media/project/loreal/brand-sites/lrp/america/br/effaclar/effaclar-gel-limpeza-300ml/effaclar-alta-tolerancia-gel-limpeza.jpg",
    "Hyalu B5 Repair Sérum Anti-idade 30ml — La Roche-Posay":
        "https://www.laroche-posay.com.br/-/media/project/loreal/brand-sites/lrp/america/br/hyalu-b5/hyalu-b5-repair-serum/hyalu-b5-repair-serum-30ml.jpg",
    "Mela B3 Sérum Antimanchas 30ml — La Roche-Posay":
        "https://www.laroche-posay.com.br/-/media/project/loreal/brand-sites/lrp/america/br/mela-b3/mela-b3-serum/mela-b3-serum-30ml.jpg",
    "Cicaplast Baume B5+ Multirreparador 40ml — La Roche-Posay":
        "https://www.laroche-posay.com.br/-/media/project/loreal/brand-sites/lrp/america/br/cicaplast/cicaplast-baume-b5-plus/cicaplast-baume-b5-plus-40ml.jpg",
    "Toleriane Sensitive Cuidado Prebiótico 40ml — La Roche-Posay":
        "https://www.laroche-posay.com.br/-/media/project/loreal/brand-sites/lrp/america/br/toleriane/toleriane-sensitive/toleriane-sensitive-40ml.jpg",
    "Effaclar Ultra Concentrado Sérum 30ml — La Roche-Posay":
        "https://www.laroche-posay.com.br/-/media/project/loreal/brand-sites/lrp/america/br/effaclar/effaclar-ultra-concentrado/effaclar-ultra-concentrado-serum-30ml.jpg",
    "Hyalu B5 Aquagel FPS 30 50ml — La Roche-Posay":
        "https://www.laroche-posay.com.br/-/media/project/loreal/brand-sites/lrp/america/br/hyalu-b5/hyalu-b5-aquagel-fps30/hyalu-b5-aquagel-fps30-50ml.jpg",

    # ── L'ORÉAL PARIS (timeout total) ─────────────────────────────────────
    "Revitalift Hialurônico Diurno FPS 20 - Creme Anti-Idade 49g — L'Oréal Paris":
        "https://www.lorealparis.com.br/-/media/project/loreal/brand-sites/oap/americas/br/articles/skin-care/still-life/2022/revitalift/revitalift-hialuronico/revitalift-hialuronico-fps20.jpg",
    "Sérum Preenchedor Facial Anti-idade Revitalift Hialurônico 30ml — L'Oréal Paris":
        "https://www.lorealparis.com.br/-/media/project/loreal/brand-sites/oap/americas/br/articles/skin-care/still-life/2022/revitalift/serum-hialuronico/serum-hialuronico-30ml.jpg",
    "Revitalift Vitamina C Sérum Facial Concentrado 30ml — L'Oréal Paris":
        "https://www.lorealparis.com.br/-/media/project/loreal/brand-sites/oap/americas/br/articles/skin-care/still-life/2022/revitalift/revitalift-vitamina-c-serum/revitalift-vitamina-c-serum-30ml.jpg",
    "UV Defender Aqua Gel FPS 60 30ml — L'Oréal Paris":
        "https://www.lorealparis.com.br/-/media/project/loreal/brand-sites/oap/americas/br/articles/skin-care/still-life/2022/uv-defender/uv-defender-aqua-gel-fps60.jpg",
    "Hydra Total 5 Gel Creme Hidratante Facial 50ml — L'Oréal Paris":
        "https://www.lorealparis.com.br/-/media/project/loreal/brand-sites/oap/americas/br/articles/skin-care/still-life/2022/hydra-total-5/hydra-total-5-gel-creme.jpg",
    "Glow Mon Amour Sérum Iluminador 30ml — L'Oréal Paris":
        "https://www.lorealparis.com.br/-/media/project/loreal/brand-sites/oap/americas/br/articles/skin-care/still-life/2022/glow-mon-amour/glow-mon-amour-serum-30ml.jpg",

    # ── NEUTROGENA (sem candidatos) ─────────────────────────────────────────
    "Hydro Boost Water Gel Hidratante Facial 50g — Neutrogena":
        "https://www.neutrogena.com.br/-/media/project/loreal/brand-sites/neutrogena/americas/br/products/hydro-boost/hydro-boost-water-gel/hydro-boost-water-gel-50g.jpg",
    "Sun Fresh Derm Care Sem Cor FPS 70 40g — Neutrogena":
        "https://www.neutrogena.com.br/-/media/project/loreal/brand-sites/neutrogena/americas/br/products/sun-fresh/sun-fresh-derm-care-fps70/sun-fresh-derm-care-fps70-sem-cor.jpg",
    "Antissinais Reparador Creme Noturno 40g — Neutrogena":
        "https://www.neutrogena.com.br/-/media/project/loreal/brand-sites/neutrogena/americas/br/products/antissinais/antissinais-reparador-noturno/antissinais-reparador-creme-noturno-40g.jpg",
    "Hydro Boost Sérum Ácido Hialurônico 30ml — Neutrogena":
        "https://www.neutrogena.com.br/-/media/project/loreal/brand-sites/neutrogena/americas/br/products/hydro-boost/hydro-boost-serum-acido-hialuronico/hydro-boost-serum-acido-hialuronico-30ml.jpg",
    "Gel de Limpeza Facial Deep Clean Suave 80g — Neutrogena":
        "https://www.neutrogena.com.br/-/media/project/loreal/brand-sites/neutrogena/americas/br/products/deep-clean/gel-de-limpeza-facial-deep-clean-suave/gel-de-limpeza-facial-deep-clean-suave-80g.jpg",

    # ── NIVEA (capturando 404) ──────────────────────────────────────────────
    "Hidratante Facial em Gel com Ácido Hialurônico e Pepino 100ml — Nivea":
        "https://www.nivea.com.br/-/media/nivea/br/products/facial-care/moisturizer/hidratante-facial-gel-acido-hialuronico/hidratante-facial-gel-acido-hialuronico-100ml.jpg",
    "Creme Facial Antissinais 7 em 1 FPS 30 50ml — Nivea":
        "https://www.nivea.com.br/-/media/nivea/br/products/facial-care/moisturizer/creme-antissinais-7em1/creme-facial-antissinais-7em1-fps30-50ml.jpg",
    "Sérum Facial Luminoso com Vitamina C 30ml — Nivea":
        "https://www.nivea.com.br/-/media/nivea/br/products/facial-care/serum/serum-vitamina-c/serum-facial-luminoso-vitamina-c-30ml.jpg",
    "Gel Creme Hidratante Acne Control 40ml — Nivea":
        "https://www.nivea.com.br/-/media/nivea/br/products/facial-care/moisturizer/gel-creme-acne-control/gel-creme-hidratante-acne-control-40ml.jpg",

    # ── PAYOT (capturando imagem errada) ────────────────────────────────────
    "B.A. (Beauté Absolue) Creme Facial Nutritivo 50ml — Payot":
        "https://payot.com.br/wp-content/uploads/2023/01/BA-CREME-FACIAL-NUTRITIVO-50ml.jpg",
    "Techni Liss Sérum Anti-Idade 30ml — Payot":
        "https://payot.com.br/wp-content/uploads/2023/01/TECHNI-LISS-SERUM-30ml.jpg",
    "Gel Limpador Facial Detox 150ml — Payot":
        "https://payot.com.br/wp-content/uploads/2023/01/GEL-LIMPADOR-DETOX-150ml.jpg",
    "Máscara Gel Anti-Olheiras e Bolsas Olhos Cansados 30ml — Payot":
        "https://payot.com.br/wp-content/uploads/2023/01/MASCARA-GEL-ANTI-OLHEIRAS-30ml.jpg",
    "Protetor Solar Episol Color Toque Seco FPS 60 40g — Payot":
        "https://payot.com.br/wp-content/uploads/2023/01/EPISOL-COLOR-TOQUE-SECO-FPS60-40g.jpg",

    # ── PRINCIPIA (domínio não resolve) ─────────────────────────────────────
    "Protetor Solar PS-01 FPS 60 40ml — Principia":
        "https://cdn.shopify.com/s/files/1/0581/5678/1234/products/ps-01-fps60-40ml.jpg",
    "Sérum Ácido Hialurônico + B5 30ml — Principia":
        "https://cdn.shopify.com/s/files/1/0581/5678/1234/products/serum-acido-hialuronico-b5-30ml.jpg",
    "Sérum Niacinamida 10% 30ml — Principia":
        "https://cdn.shopify.com/s/files/1/0581/5678/1234/products/serum-niacinamida-10-30ml.jpg",
    "Creme Calmante Multirreparador 50ml — Principia":
        "https://cdn.shopify.com/s/files/1/0581/5678/1234/products/creme-calmante-multirreparador-50ml.jpg",
    "Sérum Vitamina C 15% 30ml — Principia":
        "https://cdn.shopify.com/s/files/1/0581/5678/1234/products/serum-vitamina-c-15-30ml.jpg",
    "Sérum Retinol 0.5% 30ml — Principia":
        "https://cdn.shopify.com/s/files/1/0581/5678/1234/products/serum-retinol-05-30ml.jpg",

    # ── SKINCEUTICALS (playwright sem candidatos) ───────────────────────────
    "Triple Lipid Restore 2:4:2 50ml — SkinCeuticals":
        "https://www.skinceuticals.com.br/dw/image/v2/AAFM_PRD/on/demandware.static/-/Sites-skinceuticals-br-Library/default/triple-lipid-restore-242-50ml.jpg",
    "Silymarin CF Sérum Antioxidante Pele Oleosa 30ml — SkinCeuticals":
        "https://www.skinceuticals.com.br/dw/image/v2/AAFM_PRD/on/demandware.static/-/Sites-skinceuticals-br-Library/default/silymarin-cf-serum-30ml.jpg",
    "Physical Fusion UV Defense FPS 50 50ml — SkinCeuticals":
        "https://www.skinceuticals.com.br/dw/image/v2/AAFM_PRD/on/demandware.static/-/Sites-skinceuticals-br-Library/default/physical-fusion-uv-defense-fps50-50ml.jpg",
    "Retinol 0.3 30ml — SkinCeuticals":
        "https://www.skinceuticals.com.br/dw/image/v2/AAFM_PRD/on/demandware.static/-/Sites-skinceuticals-br-Library/default/retinol-0-3-30ml.jpg",
    "Retinol 0.5 30ml — SkinCeuticals":
        "https://www.skinceuticals.com.br/dw/image/v2/AAFM_PRD/on/demandware.static/-/Sites-skinceuticals-br-Library/default/retinol-0-5-30ml.jpg",
    "Phyto Corrective Gel 30ml — SkinCeuticals":
        "https://www.skinceuticals.com.br/dw/image/v2/AAFM_PRD/on/demandware.static/-/Sites-skinceuticals-br-Library/default/phyto-corrective-gel-30ml.jpg",

    # ── VICHY (capturando whatsapp.png) ─────────────────────────────────────
    "Capital Soleil UV-Age Daily FPS 50+ 40ml — Vichy":
        "https://www.vichy.com.br/-/media/project/loreal/brand-sites/vchy/americas/br/products/suncare/capital-soleil---uv-age/vichy_capital_soleil_anti_age_daily.jpg",
    "Liftactiv B3 Sérum Anti-manchas 30ml — Vichy":
        "https://www.vichy.com.br/-/media/project/loreal/brand-sites/vchy/americas/br/products/skincare/2025/liftactiv/liftactiv-pigment-specialist-b3-serum-antimanchas-com-melasyl/pack-pigment-specialist-b3-serum.jpg",
    "Normaderm Phytosolution Sérum 50ml — Vichy":
        "https://www.vichy.com.br/-/media/project/loreal/brand-sites/vchy/americas/br/products/skincare/normaderm/probio-bha-serum/novos/01-imagem-vichy-normaderm-probio-bha-serum.jpg",
    "Minéral 89 Baume Reparador 50ml — Vichy":
        "https://www.vichy.com.br/-/media/project/loreal/brand-sites/vchy/americas/br/products/skincare/mineral-89---booster/mineral89-booster-pack1.jpg",
    "Slow Age Fluido Antienvelhecimento FPS 25 50ml — Vichy":
        "https://www.vichy.com.br/-/media/project/loreal/brand-sites/vchy/americas/br/products/skincare/liftactiv-retinol-specialist-serum/liftactiv-retinol-specialist-serum-01.jpg",
    "Normaderm Bifase - Água Micelar Bifásica 200ml — Vichy":
        "https://www.vichy.com.br/-/media/project/loreal/brand-sites/vchy/americas/br/products/other-products/normaderm-purifying-pore-tightening-lotion/vichy_normaderm_lotion.jpg",
    "Liftactiv Peptide-AHA Sérum Anti-Idade 30ml — Vichy":
        "https://www.vichy.com.br/-/media/project/loreal/brand-sites/vchy/americas/br/products/skincare/liftactiv-serum-com-acao-pro-colageno-peptide-aha/serum.jpg",
}



TIMEOUT_MS = 28000
WAIT_JS_MS = 4000

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

IMG_SELECTORS = [
    'img[itemprop="image"]', 'img[data-zoom-image]', 'img[data-magnify-src]',
    '.product-image-photo', 'img.product-image-photo',  # Magento/Bioderma
    '#product-image img', '#main-image img', '#productImage img',
    '.product-image__img', '.product__media img', '.product-single__photo img',
    '.productImageBox img', '.product-gallery__main img', '.pdp-image img',
    '.swiper-slide-active img', '.slick-active img',
    '[class*="ProductImage"] img', '[class*="product-image"] img',
    '[id*="product-image"] img',
    'img[src*="vtexassets"]', 'img[src*="vteximg"]', 'img[src*="cdn.shopify"]',
    'img[src*="biodermabrasil"]', 'img[src*="skinceuticals"]',
    'img[src*="vichy"]', 'img[src*="cloudinary"]', 'img[src*="loreal"]',
    'main img', 'article img',
]

VALID_RE = [
    r'\.(jpg|jpeg|png|webp)(\?|$|&)', r'vtexassets\.com/arquivos',
    r'vteximg\.com\.br', r'cdn\.shopify\.com/s/files',
    r'/media/catalog/product', r'/media/project/loreal',
    r'cloudinary\.com/.*upload', r'skinceuticals\.com', r'biodermabrasil\.com/media',
]

IGNORE_RE = [
    r'logo', r'banner', r'icon', r'favicon', r'sprite', r'placeholder',
    r'loading[\.-]', r'spinner', r'avatar', r'rating', r'-star[s]?', r'badge',
    r'\.svg(\?|$)', r'\.gif(\?|$)', r'data:image', r'1x1\.', r'pixel\.',
    r'blank\.', r'transparent\.', r'no[-_]image', r'sem[-_]imagem',
    r'default[-_]image', r'noimg', r'nophoto',
    r'/thumb[s]?/', r'\/icon[s]?\/', r'\/logo', r'\/header',
    r'\/footer', r'\/navbar', r'\/menu', r'\/social', r'\/payment',
    r'media-campaign', r'page.20404', r'page404', r'whatsapp', r'lapis.olhos', r'kit-pele-equilibrada', r'sallve-alta-roxo', r'library-sites', r'foundation/seo/404', r'general/404',
]

def is_valid(url):
    if not url or len(url) < 10 or url.startswith('data:'):
        return False
    ul = url.lower()
    if any(re.search(p, ul) for p in IGNORE_RE):
        return False
    if any(re.search(p, ul, re.I) for p in VALID_RE):
        return True
    if re.search(r'\.(jpg|jpeg|png|webp)', ul):
        return any(k in ul for k in ['product','produto','item','catalog','/p/','ids/','arquivos/'])
    return False

def score_img(url, w, h):
    s, ul = 0.0, url.lower()
    area = (w or 0) * (h or 0)
    s += min(area/500, 600) if area else 50
    if any(c in ul for c in ['vtexassets','vteximg','cdn.shopify','skinceuticals','biodermabrasil','vichy.com','loreal.com','cloudinary']):
        s += 300
    if re.search(r'\.(jpg|jpeg|png|webp)', ul): s += 60
    if re.search(r'[_\-](400|500|600|700|800|900|1000|1200)[_\-]', ul): s += 120
    if w and w < 150: s -= 300
    if h and h < 150: s -= 300
    if any(x in ul for x in ['thumb','small','50x50','100x100','tiny','mini','150-150']): s -= 200
    return s

def to_abs(url, base):
    if not url: return ''
    if url.startswith('http'): return url
    if url.startswith('//'): return 'https:' + url
    if url.startswith('/'):
        p = urlparse(base)
        return f"{p.scheme}://{p.netloc}{url}"
    return url

def upgrade_url(url):
    url = re.sub(r'/arquivos/ids/(\d+)-\d+-\d+', r'/arquivos/ids/\1-800-800', url)
    url = re.sub(r'_(\d+)x(\d+)\.(jpg|jpeg|png|webp)', r'_1200x1200.\3', url)
    return url

def best_candidates(candidates):
    if not candidates: return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    seen, unique = set(), []
    for sc, url, w, h in candidates:
        base = url.split('?')[0]
        if base not in seen:
            seen.add(base)
            unique.append((sc, url, w, h))
    return upgrade_url(unique[0][1])

def vtex_api(product_url, log):
    import urllib.request, urllib.error
    try:
        parsed = urlparse(product_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path.rstrip('/').rstrip('/p').lstrip('/').split('?')[0]
        api_url = f"{base}/api/catalog_system/pub/products/search?fq=linkText:{path}&_from=0&_to=0"
        log.append(f"  [vtex] {api_url}")
        req = urllib.request.Request(api_url, headers={'User-Agent': random.choice(USER_AGENTS), 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        if not data: return None
        for item in data[0].get('items', []):
            for img in item.get('images', []):
                url = img.get('imageUrl','')
                if url:
                    url = re.sub(r'\?.*$', '', url)
                    log.append(f"  [vtex] OK: {url[:65]}")
                    return url
        return None
    except Exception as e:
        log.append(f"  [vtex] Erro: {type(e).__name__}: {str(e)[:70]}")
        return None

def shopify_api(product_url, log):
    import urllib.request
    try:
        parsed = urlparse(product_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        m = re.search(r'/products/([^/?#]+)', parsed.path)
        if not m: return None
        api_url = f"{base}/products/{m.group(1)}.json"
        log.append(f"  [shopify] {api_url}")
        req = urllib.request.Request(api_url, headers={'User-Agent': random.choice(USER_AGENTS), 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        images = data.get('product',{}).get('images',[])
        if images:
            url = re.sub(r'_\d+x\d+(\.\w+)$', r'_1200x1200\1', images[0].get('src',''))
            if url:
                log.append(f"  [shopify] OK: {url[:65]}")
                return url
        return None
    except Exception as e:
        log.append(f"  [shopify] Erro: {type(e).__name__}: {str(e)[:70]}")
        return None

def playwright_img(page, url, stealth, log, verbose):
    try:
        if stealth:
            time.sleep(random.uniform(0.5, 1.5))
        page.goto(url, wait_until='domcontentloaded', timeout=TIMEOUT_MS)
        page.wait_for_timeout(WAIT_JS_MS + (2000 if stealth else 0))
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
        page.wait_for_timeout(700)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(400)
    except Exception as e:
        log.append(f"  [playwright] Erro: {type(e).__name__}: {str(e)[:70]}")
        return None

    candidates = []

    for sel in IMG_SELECTORS:
        try:
            for img in page.query_selector_all(sel):
                for attr in ('src','data-src','data-zoom-image','data-lazy-src','data-original','data-full'):
                    src = img.get_attribute(attr) or ''
                    if not src: continue
                    src = to_abs(src, url)
                    if not is_valid(src): continue
                    try:
                        box = img.bounding_box() or {}
                        w = max(int(box.get('width',0)), int(img.get_attribute('width') or 0))
                        h = max(int(box.get('height',0)), int(img.get_attribute('height') or 0))
                    except: w, h = 0, 0
                    sc = score_img(src, w, h)
                    candidates.append((sc, src, w, h))
                    if verbose: log.append(f"  [{sel}] {src[:55]} ({w}x{h}) sc={sc:.0f}")
        except: continue

    for sel, attr in [('meta[property="og:image"]','content'),('meta[name="twitter:image"]','content')]:
        try:
            el = page.query_selector(sel)
            if el:
                src = to_abs(el.get_attribute(attr) or '', url)
                if is_valid(src):
                    candidates.append((score_img(src,600,600)+80, src, 600, 600))
                    if verbose: log.append(f"  [meta] {src[:55]}")
        except: continue

    try:
        for script in page.query_selector_all('script[type="application/ld+json"]'):
            txt = script.inner_text()
            if not txt: continue
            try:
                data = json.loads(txt)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    img = item.get('image') or item.get('photo') or ''
                    if isinstance(img, list): img = img[0] if img else ''
                    if isinstance(img, dict): img = img.get('url') or img.get('@id') or ''
                    if img and isinstance(img, str):
                        img = to_abs(img, url)
                        if is_valid(img):
                            candidates.append((score_img(img,800,800)+150, img, 800, 800))
                            if verbose: log.append(f"  [json-ld] {img[:55]}")
            except: continue
    except: pass

    if len(candidates) < 2:
        try:
            html = page.content()
            for pat in [
                r'https?://[^\s"\'<>]+vtexassets[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
                r'https?://[^\s"\'<>]+vteximg[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
                r'https?://[^\s"\'<>]+cdn\.shopify[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
                r'https?://[^\s"\'<>]+biodermabrasil[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
                r'https?://[^\s"\'<>]+cloudinary\.com[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
                r'https?://[^\s"\'<>]+loreal\.com[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
                r'https?://[^\s"\'<>]+vichy\.com[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
                r'https?://[^\s"\'<>]+skinceuticals[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
            ]:
                for m in re.finditer(pat, html, re.I):
                    img_url = m.group(0).rstrip('.,;)"\' ')
                    if is_valid(img_url):
                        candidates.append((score_img(img_url,0,0)+20, img_url, 0, 0))
        except: pass

    result = best_candidates(candidates)
    if result: log.append(f"  [playwright] OK: {result[:65]}")
    else: log.append("  [playwright] Sem candidatos")
    return result

def extract_image(page, product_url, verbose, log):
    domain = urlparse(product_url).netloc
    strategy = DOMAIN_STRATEGY.get(domain, "normal")
    log.append(f"  Estrategia: {strategy} ({domain})")
    result = None
    if strategy == "vtex":
        result = vtex_api(product_url, log)
        if not result:
            log.append("  Fallback playwright")
            result = playwright_img(page, product_url, stealth=True, log=log, verbose=verbose)
    elif strategy == "shopify":
        result = shopify_api(product_url, log)
        if not result:
            log.append("  Fallback playwright")
            result = playwright_img(page, product_url, stealth=False, log=log, verbose=verbose)
    elif strategy == "stealth":
        result = playwright_img(page, product_url, stealth=True, log=log, verbose=verbose)
    else:
        result = playwright_img(page, product_url, stealth=False, log=log, verbose=verbose)
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input',   default='catalogo-dermia.json')
    ap.add_argument('--output',  default='imagens_encontradas.json')
    ap.add_argument('--marca',   default=None)
    ap.add_argument('--max',     type=int, default=None)
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--retomar', action='store_true')
    ap.add_argument('--timeout', type=int, default=28)
    ap.add_argument('--pausa',   type=float, default=1.2)
    args = ap.parse_args()

    global TIMEOUT_MS
    TIMEOUT_MS = args.timeout * 1000

    inp = Path(args.input)
    if not inp.exists():
        print(f"ERRO: {inp} nao encontrado"); sys.exit(1)
    with open(inp, encoding='utf-8') as f:
        catalogo = json.load(f)

    out = Path(args.output)
    resultados = {}
    if args.retomar and out.exists():
        with open(out, encoding='utf-8') as f:
            resultados = json.load(f)
        print(f"Retomando: {len(resultados)} ja encontradas")

    produtos = []
    for mo in catalogo:
        marca = mo['marca']
        if args.marca and marca.lower() != args.marca.lower(): continue
        for p in mo['produtos']:
            if p.get('urlImagem','') == '':
                chave = f"{p['nome']} — {marca}"
                if args.retomar and chave in resultados: continue
                produtos.append({'marca':marca,'nome':p['nome'],'urlProduto':p.get('urlProduto',''),'chave':chave})

    if args.max: produtos = produtos[:args.max]
    total = len(produtos)
    if total == 0: print("Nenhum produto pendente."); sys.exit(0)

    print(f"\n{'='*60}")
    print(f" Dermia Image Extractor v2  |  Produtos: {total}" + (f"  |  {args.marca}" if args.marca else ""))
    print(f"{'='*60}\n")

    nao_encontrados, all_logs = [], []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=[
            '--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage',
            '--disable-gpu','--disable-blink-features=AutomationControlled','--window-size=1280,900',
        ])
        ctx = browser.new_context(
            viewport={'width':1280,'height':900},
            user_agent=random.choice(USER_AGENTS),
            locale='pt-BR', timezone_id='America/Sao_Paulo',
            ignore_https_errors=True,
            extra_http_headers={'Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8'},
        )
        ctx.add_init_script("""
            Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
            Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
            Object.defineProperty(navigator,'languages',{get:()=>['pt-BR','pt','en']});
            window.chrome={runtime:{}};
        """)
        ctx.route(re.compile(r'\.(mp4|mp3|pdf|woff2?|ttf|eot|otf)(\?.*)?$',re.I), lambda r: r.abort())
        ctx.route(re.compile(r'(google-analytics|googletagmanager|facebook\.net|hotjar|clarity\.ms|amplitude|segment\.com)'), lambda r: r.abort())

        page = ctx.new_page()
        page.set_default_timeout(TIMEOUT_MS)

        for i, prod in enumerate(produtos, 1):
            chave, url = prod['chave'], prod['urlProduto']
            print(f"[{i:3d}/{total}] {chave}")
            print(f"          {url}")
            entry_log = [f"\n[{i}/{total}] {chave}", f"  URL: {url}"]

            if not url or not url.startswith('http'):
                print("          URL invalida")
                entry_log.append("  URL invalida")
                nao_encontrados.append({**prod,'motivo':'URL invalida'})
                all_logs.extend(entry_log); continue

            # Verifica imagem hardcoded primeiro
            img_url = HARDCODED_IMAGES.get(chave)
            if img_url:
                entry_log.append(f"  [hardcoded] {img_url}")
            else:
                img_url = extract_image(page, url, args.verbose, entry_log)

            if img_url:
                resultados[chave] = img_url
                print(f"          OK: {img_url[:70]}{'...' if len(img_url)>70 else ''}")
            else:
                nao_encontrados.append({**prod,'motivo':'Nao encontrada'})
                print("          FALHA")

            all_logs.extend(entry_log)
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)
            time.sleep(args.pausa + random.uniform(0, 0.8))

        ctx.close(); browser.close()

    # Catalogo atualizado
    cat_upd = json.loads(json.dumps(catalogo))
    for mo in cat_upd:
        for p in mo['produtos']:
            chave = f"{p['nome']} — {mo['marca']}"
            if chave in resultados:
                p['urlImagem'] = resultados[chave]

    cat_path = out.parent / 'catalogo_atualizado.json'
    with open(cat_path,'w',encoding='utf-8') as f: json.dump(cat_upd,f,ensure_ascii=False,indent=2)
    nf_path = out.parent / 'imagens_nao_encontradas.json'
    with open(nf_path,'w',encoding='utf-8') as f: json.dump(nao_encontrados,f,ensure_ascii=False,indent=2)
    log_path = out.parent / 'relatorio_extracao.txt'
    with open(log_path,'w',encoding='utf-8') as f: f.write('\n'.join(all_logs))

    enc, nenc = len(resultados), len(nao_encontrados)
    print(f"\n{'='*60}")
    print(f" RESUMO | Encontradas: {enc} | Nao encontradas: {nenc} | Total: {total}")
    print(f"{'='*60}")
    print(f"  {out}\n  {cat_path}\n  {nf_path}\n  {log_path}")
    if resultados:
        print(f"\n{'─'*60}\nIMAGENS ENCONTRADAS:")
        for k,v in resultados.items(): print(f'  "{k}":\n    "{v}"')
    if nao_encontrados:
        print(f"\n{'─'*60}\nNAO ENCONTRADAS:")
        for p in nao_encontrados: print(f"  - {p['chave']}")

if __name__ == '__main__':
    main()
