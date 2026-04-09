# SPDX-License-Identifier: EUPL-1.2
from django.urls import path
from . import views

app_name = "datenschutz"

urlpatterns = [
    path("",                              views.dashboard,               name="dashboard"),
    path("auskunft.pdf",                  views.auskunft_pdf,            name="auskunft_pdf"),
    path("auskunft/suche/",               views.auskunft_suche,          name="auskunft_suche"),
    path("auskunft/suche/pdf/",           views.auskunft_suche_pdf,      name="auskunft_suche_pdf"),
    path("protokoll/<int:pk>/",           views.loeschprotokoll_detail,  name="protokoll_detail"),
    path("protokoll/<int:pk>/download/",  views.loeschprotokoll_pdf_download, name="protokoll_pdf"),
]
