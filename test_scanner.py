"""
Tests unitaires pour TikTokVideoAnalyzer et Safe Zone.
Vérifie le bon fonctionnement du pipeline complet sur une vraie vidéo.
"""

import os
import cv2
from analyzer import TikTokVideoAnalyzer
from safe_zone import render_tiktok_overlay, get_tiktok_safe_zone_rects


def test_analyzer():
    video_path = "demo_sample.mp4"
    assert os.path.exists(video_path), "demo_sample.mp4 doit exister"

    analyzer = TikTokVideoAnalyzer(video_path)

    # Test avec style 'action'
    res_action = analyzer.analyze_all(content_style="action")
    assert "overall_score" in res_action
    assert 0 <= res_action["overall_score"] <= 100
    assert res_action["technical"]["is_9_16"] is True
    assert res_action["technical"]["duration"] > 0
    assert "scores" in res_action
    assert "checks" in res_action
    print(f"✅ Test style 'action' réussi - Score global: {res_action['overall_score']}/100")

    # Test avec style 'statique'
    res_stat = analyzer.analyze_all(content_style="statique")
    assert "overall_score" in res_stat
    print(f"✅ Test style 'statique' réussi - Score global: {res_stat['overall_score']}/100")

    # Test de la Safe Zone
    zones = get_tiktok_safe_zone_rects(1080, 1920)
    assert "safe_box" in zones
    assert "right_sidebar" in zones

    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    assert ret, "Lecture de frame échouée"

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    overlaid = render_tiktok_overlay(frame_rgb)
    assert overlaid.shape == frame_rgb.shape
    print("✅ Test de rendu Safe Zone TikTok réussi")

    print("\n🎉 TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS !")


if __name__ == "__main__":
    test_analyzer()
