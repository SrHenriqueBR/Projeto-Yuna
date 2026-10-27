"""Primeiro corpo 2D da Yuna: chibi vetorial, transparente e interativo.

Não requer imagens, Godot, rede, GPU dedicada ou arquivos adicionais. É uma
BASE VISUAL estilizada para posterior substituição por arte anime em camadas.
"""
import math
import time

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from avatar_state import HAIR, EYES, OUTFITS, load_style


class YunaAvatar(QWidget):
    """Personagem opcional sobre a área de trabalho; não recebe entrada de voz."""
    def __init__(self, root, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.root = root
        self.setObjectName("YunaAvatar")
        self.setWindowTitle("Yuna • Avatar 2D")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFixedSize(190, 277)
        self.appearance = load_style(root)
        self.pose = "idle"
        self.pose_until = 0.0
        self.bubble = ""
        self.bubble_until = 0.0
        self.drag_start = None
        self.tick_count = 0
        self.step = 1
        self.x_coordinate = 0.0
        self._position_initial()
        self.animation = QTimer(self)
        self.animation.setInterval(80)
        self.animation.timeout.connect(self.advance)
        self.animation.start()

    def _position_initial(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.move(80, 80)
            return
        r = screen.availableGeometry()
        self.move(max(r.left(), r.right() - 235),
                  max(r.top(), r.bottom() - self.height() - 10))
        self.x_coordinate = float(self.x())

    def reload_appearance(self):
        self.appearance = load_style(self.root)
        self.update()

    def set_pose(self, pose, seconds=4, phrase=""):
        if pose not in ("idle", "walk", "sit", "angry", "happy", "talk"):
            return
        self.pose = pose
        self.pose_until = time.monotonic() + max(0, float(seconds))
        if phrase:
            self.bubble = phrase[:60]
            self.bubble_until = self.pose_until
        self.update()

    def visible_pose(self):
        if time.monotonic() < self.pose_until:
            return self.pose
        if self.appearance["walking"]:
            # Intervalos de descanso, sem inferir emoções reais.
            return "sit" if self.tick_count % 700 >= 510 else "walk"
        return "idle"

    def advance(self):
        self.tick_count += 1
        if not self.isVisible():
            return
        if self.drag_start is None and self.visible_pose() == "walk":
            screen = QApplication.screenAt(self.geometry().center())
            if screen is None:
                screen = QApplication.primaryScreen()
            if screen is not None:
                rect = screen.availableGeometry()
                cursor = QCursor.pos()
                close_cursor = (
                    abs(cursor.x() - self.geometry().center().x()) < 105
                    and abs(cursor.y() - self.geometry().center().y()) < 155
                )
                if not close_cursor:
                    self.x_coordinate += self.step * 0.45
                    low, high = rect.left(), rect.right() - self.width() + 1
                    if self.x_coordinate < low or self.x_coordinate > high:
                        self.step *= -1
                        self.x_coordinate = min(high, max(low, self.x_coordinate))
                    self.move(round(self.x_coordinate), self.y())
        self.update()

    def enterEvent(self, event):
        if self.drag_start is None:
            self.set_pose("idle", seconds=1.1, phrase="Opa, Kaizen!")
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self.set_pose("angry", 3.0, "Ei! Nada de me cutucar! >:(")
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.show_menu(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start is not None:
            target = event.globalPosition().toPoint() - self.drag_start
            self.move(target)
            self.x_coordinate = float(self.x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def show_menu(self, point):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#211a33;color:#f7f0ff;border:1px solid #745ba2;}"
            "QMenu::item{padding:9px 20px;}QMenu::item:selected{background:#59437d;}"
        )
        sit = menu.addAction("Sentar")
        stand = menu.addAction("Levantar")
        pause = menu.addAction("Pausar caminhada" if self.appearance["walking"]
                               else "Permitir caminhada")
        menu.addSeparator()
        hair_menu = menu.addMenu("Cabelo")
        hair_choices = {hair_menu.addAction(name.title()): ("hair", name)
                        for name in HAIR}
        eye_menu = menu.addMenu("Olhos")
        eye_choices = {eye_menu.addAction(name.title()): ("eyes", name)
                       for name in EYES}
        outfit_menu = menu.addMenu("Roupa")
        outfit_choices = {outfit_menu.addAction(name.title()): ("outfit", name)
                          for name in OUTFITS}
        menu.addSeparator()
        hide = menu.addAction("Esconder avatar")
        chosen = menu.exec(point)
        chosen_style = (hair_choices | eye_choices | outfit_choices).get(chosen)
        if chosen_style is not None:
            from avatar_state import save_style
            key, color = chosen_style
            self.appearance[key] = color
            save_style(self.root, self.appearance)
            self.set_pose("happy", seconds=2, phrase="Visual novo! 🖤")
            return
        if chosen == sit:
            self.set_pose("sit", seconds=25, phrase="Uma pausa... 🖤")
        elif chosen == stand:
            self.set_pose("idle", seconds=7)
        elif chosen == pause:
            from avatar_state import save_style
            self.appearance["walking"] = not self.appearance["walking"]
            save_style(self.root, self.appearance)
            self.set_pose("idle", seconds=1)
        elif chosen == hide:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        pose = self.visible_pose()
        now = time.monotonic()
        wave = math.sin(self.tick_count * 0.23)
        sway = 2.0 * wave if pose in ("walk", "happy", "talk") else 0.0
        hair = QColor(HAIR[self.appearance["hair"]])
        eyes = QColor(EYES[self.appearance["eyes"]])
        dress = QColor(OUTFITS[self.appearance["outfit"]])
        shadow = QColor("#171125")
        skin = QColor("#f5d8d8")

        # Sombra de apoio; no modo sentado, o corpo desce e as pernas dobram.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(22, 14, 38, 95))
        painter.drawEllipse(QRectF(32, 249, 126, 17))

        painter.save()
        painter.translate(95, 0)
        if self.step < 0 and pose == "walk":
            painter.scale(-1, 1)
        painter.translate(0, sway)

        sitting = pose == "sit"
        vertical = 30 if sitting else 0

        # Cabelos de trás, incluindo duas mechas longas e laterais.
        painter.setPen(QPen(shadow, 2.2))
        painter.setBrush(hair)
        painter.drawRoundedRect(QRectF(-57, 63 + vertical, 114, 133), 43, 34)
        painter.drawEllipse(QRectF(-62, 95 + vertical, 26, 111))
        painter.drawEllipse(QRectF(37, 95 + vertical, 26, 111))

        # Pernas, sapatinhos e caminhada alternada.
        if sitting:
            painter.setPen(QPen(shadow, 10, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(-22, 210 + vertical), QPointF(-48, 236))
            painter.drawLine(QPointF(22, 210 + vertical), QPointF(48, 236))
        else:
            pace = wave * 7 if pose == "walk" else 0
            painter.setPen(QPen(shadow, 12, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(-17, 205), QPointF(-19 + pace, 249))
            painter.drawLine(QPointF(17, 205), QPointF(19 - pace, 249))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#443152"))
        painter.drawEllipse(QRectF(-37, 241, 33, 12))
        painter.drawEllipse(QRectF(4, 241, 33, 12))

        # Vestido em camadas com detalhes discretos.
        hem = QPainterPath()
        hem.moveTo(-23, 163 + vertical)
        hem.lineTo(23, 163 + vertical)
        hem.lineTo(48, 220 + vertical)
        hem.quadTo(0, 230 + vertical, -48, 220 + vertical)
        hem.closeSubpath()
        painter.setPen(QPen(shadow, 2.3))
        painter.setBrush(dress)
        painter.drawPath(hem)
        painter.setPen(QPen(QColor("#b39bd1"), 2))
        painter.drawLine(QPointF(-43, 213 + vertical), QPointF(43, 213 + vertical))
        painter.setPen(QPen(QColor("#e7c6ec"), 1.8))
        painter.drawLine(QPointF(0, 165 + vertical), QPointF(0, 201 + vertical))
        painter.setBrush(QColor("#bda2d7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(-5, 185 + vertical, 10, 10))

        # Braços (em estado bravo, os dois apoiam na cintura).
        painter.setPen(QPen(skin, 11, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        if pose == "angry":
            painter.drawLine(QPointF(-23, 171 + vertical), QPointF(-40, 185 + vertical))
            painter.drawLine(QPointF(23, 171 + vertical), QPointF(40, 185 + vertical))
        else:
            painter.drawLine(QPointF(-25, 169 + vertical),
                             QPointF(-47, 193 + vertical + wave * 3))
            painter.drawLine(QPointF(25, 169 + vertical),
                             QPointF(46, 192 + vertical - wave * 3))

        # Cabeça chibi e franja em três pontas.
        painter.setPen(QPen(shadow, 2.4))
        painter.setBrush(skin)
        painter.drawEllipse(QRectF(-50, 71 + vertical, 100, 94))
        painter.setBrush(hair)
        crown = QPainterPath()
        crown.moveTo(-53, 112 + vertical)
        crown.quadTo(-66, 47 + vertical, 0, 54 + vertical)
        crown.quadTo(64, 50 + vertical, 53, 111 + vertical)
        crown.quadTo(41, 101 + vertical, 32, 86 + vertical)
        crown.quadTo(13, 111 + vertical, 1, 101 + vertical)
        crown.quadTo(-10, 111 + vertical, -16, 92 + vertical)
        crown.quadTo(-32, 111 + vertical, -53, 112 + vertical)
        painter.drawPath(crown)

        # Olhos e sobrancelhas mudam com a reação ao clique.
        painter.setBrush(QColor("#fff8f8"))
        painter.setPen(QPen(shadow, 2))
        painter.drawEllipse(QRectF(-35, 117 + vertical, 25, 25))
        painter.drawEllipse(QRectF(10, 117 + vertical, 25, 25))
        painter.setBrush(eyes)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(-27, 122 + vertical, 13, 16))
        painter.drawEllipse(QRectF(14, 122 + vertical, 13, 16))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(-23, 125 + vertical, 5, 5))
        painter.drawEllipse(QRectF(18, 125 + vertical, 5, 5))
        painter.setPen(QPen(shadow, 3, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        if pose == "angry":
            painter.drawLine(-36, 111 + vertical, -12, 118 + vertical)
            painter.drawLine(12, 118 + vertical, 36, 111 + vertical)
        else:
            painter.drawLine(-35, 112 + vertical, -14, 111 + vertical)
            painter.drawLine(14, 111 + vertical, 35, 112 + vertical)

        # Bochechas e boca expressiva, sem atribuir sentimentos reais à IA.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(233, 130, 153, 95))
        painter.drawEllipse(QRectF(-43, 139 + vertical, 15, 6))
        painter.drawEllipse(QRectF(28, 139 + vertical, 15, 6))
        painter.setPen(QPen(QColor("#6e3c5c"), 2))
        if pose == "angry":
            painter.drawArc(QRectF(-8, 153 + vertical, 16, 10), 0, 180 * 16)
        elif pose in ("happy", "talk"):
            painter.drawArc(QRectF(-9, 146 + vertical, 18, 13),
                            180 * 16, 180 * 16)
        else:
            painter.drawArc(QRectF(-8, 147 + vertical, 16, 9),
                            190 * 16, 155 * 16)
        painter.restore()

        # Balão opcional; o avatar não lê arquivos, microfone ou janela de terceiros.
        if self.bubble and now < self.bubble_until:
            painter.setPen(QPen(QColor("#8b6cb9"), 1.6))
            painter.setBrush(QColor("#28213d"))
            painter.drawRoundedRect(QRectF(9, 6, 172, 43), 10, 10)
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#f5ecff"))
            painter.drawText(QRectF(17, 11, 156, 31),
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                             self.bubble)
        painter.end()


def main():
    import sys
    from pathlib import Path
    app = QApplication(sys.argv)
    avatar = YunaAvatar(Path(__file__).resolve().parent)
    avatar.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
