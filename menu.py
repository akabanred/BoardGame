import os
import sys
import time
import subprocess
import pygame


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

WIDTH, HEIGHT = 520, 360
BACKGROUND = (245, 248, 252)
BLACK = (20, 24, 33)
MUTED = (115, 120, 130)
HILIGHT = (50, 80, 220)
LINE = (205, 210, 220)


def load_fonts():
	candidates = ["Segoe UI", "Arial", "Helvetica", "Roboto", None]
	for name in candidates:
		try:
			title_f = pygame.font.SysFont(name, 42, bold=True)
			button_f = pygame.font.SysFont(name, 24, bold=True)
			tiny_f = pygame.font.SysFont(name, 18)
			_ = title_f.render("CỜ GÁNH", True, BLACK)
			return title_f, button_f, tiny_f
		except Exception:
			continue
	return (
		pygame.font.SysFont(None, 42, bold=True),
		pygame.font.SysFont(None, 24, bold=True),
		pygame.font.SysFont(None, 18),
	)


class Button:
	def __init__(self, rect, text, font, on_click):
		self.rect = pygame.Rect(rect)
		self.text = text
		self.font = font
		self.on_click = on_click

	def draw(self, surf):
		mx, my = pygame.mouse.get_pos()
		hover = self.rect.collidepoint(mx, my)
		base = (234, 238, 245)
		if hover:
			base = (220, 226, 236)
		pygame.draw.rect(surf, base, self.rect, border_radius=12)
		pygame.draw.rect(surf, LINE, self.rect, 2, border_radius=12)
		txt = self.font.render(self.text, True, BLACK if not hover else HILIGHT)
		surf.blit(txt, txt.get_rect(center=self.rect.center))

	def handle(self, event):
		if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
			if self.rect.collidepoint(event.pos):
				self.on_click()
				return True
		return False


def launch_script(script_name, *, new_console=True):
	script_path = os.path.join(BASE_DIR, script_name)
	if not os.path.exists(script_path):
		return f"Không tìm thấy {script_name}"

	cmd = [sys.executable, script_path]
	kwargs = {"cwd": BASE_DIR}
	if new_console and NEW_CONSOLE:
		kwargs["creationflags"] = NEW_CONSOLE

	try:
		subprocess.Popen(cmd, **kwargs)
		return None
	except Exception as exc:
		return str(exc)


def main():
	pygame.init()
	screen = pygame.display.set_mode((WIDTH, HEIGHT))
	pygame.display.set_caption("Cờ Gánh - Menu")
	title_f, button_f, tiny_f = load_fonts()
	clock = pygame.time.Clock()

	# status_message = "Chọn chế độ chơi"

	def set_status(message):
		# nonlocal status_message
		status_message = message

	def play_vs_ai():
		err = launch_script("ai.py")
		if err:
			set_status(f"Lỗi mở AI: {err}")
		else:
			set_status("Đã mở chế độ AI trong cửa sổ mới.")

	def play_online():
		order = ["server.py", "client1.py", "client2.py"]
		for idx, name in enumerate(order):
			err = launch_script(name)
			if err:
				set_status(f"Lỗi mở {name}: {err}")
				return
			if idx == 0:
				# Cho server một chút thời gian trước khi mở client
				time.sleep(0.5)

	def exit_app():
		pygame.quit()
		sys.exit()

	buttons = [
		Button((WIDTH // 2 - 140, 120, 280, 56), "Play vs AI", button_f, play_vs_ai),
		Button((WIDTH // 2 - 140, 192, 280, 56), "Play Online", button_f, play_online),
		Button((WIDTH // 2 - 140, 264, 280, 56), "Exit", button_f, exit_app),
	]


	while True:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				exit_app()
			for btn in buttons:
				if btn.handle(event):
					break

		screen.fill(BACKGROUND)

		title = title_f.render("CỜ GÁNH", True, BLACK)
		screen.blit(title, title.get_rect(center=(WIDTH // 2, 60)))

		for btn in buttons:
			btn.draw(screen)
		pygame.display.flip()
		clock.tick(60)


if __name__ == "__main__":
	main()
