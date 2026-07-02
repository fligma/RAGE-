import os
import sys
import math
import random
from os import environ

GAME_TITLE      = "RAGE!!!!"
BRAND_LOGO_TEXT = "Fligma"
environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame

def asset_path(name):
    return os.path.join(ASSET_DIR, name)

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
icon= pygame.image.load(asset_path("icon.png"))
ASSET_BULLET    = "bullet(16x16).png"
ASSET_PLAYER    = "player(64x32).png"
ASSET_GROUND    = "ground(128x128).png"
ASSET_ENEMY_W1  = "enemy_walk1(64x64).png"
ASSET_ENEMY_W2  = "enemy_walk2(64x64).png"
ASSET_ENEMY_H1  = "enemy_hit1(64x64).png"
ASSET_ENEMY_H2  = "enemy_hit2(64x64).png"
pygame.mixer.init()
GUN_SOUND = pygame.mixer.Sound(asset_path("gun_shot.mp3"))
MUSIC_GAMEOVER = pygame.mixer.Sound(asset_path("gameover.wav"))

GLOBAL_SETTINGS = {
    "fullscreen": False
}

def load_and_scale(path, w, h):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (w, h))
    except Exception:
        return None

def play_music(music_file):
    pygame.mixer.music.load(music_file)
    pygame.mixer.music.play(-1)

class Bullet:
    def __init__(self, x, y, dx, dy):
        GUN_SOUND.play()
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.speed = 500
        self.life = 2.0
        self.hit_timer = 0
        self.image = load_and_scale(asset_path(ASSET_BULLET), 8, 8)
        self.rect = pygame.Rect(x - 4, y - 4, 8, 8)

    def update(self, dt):
        self.x += self.dx * self.speed * dt
        self.y += self.dy * self.speed * dt
        self.rect.center = (self.x, self.y)
        if self.hit_timer>0:
            self.hit_timer-=dt
        self.life -= dt

    def draw(self, surface, cam_x, cam_y):
        if self.image:
            surface.blit(self.image, (self.x - cam_x - 4, self.y - cam_y - 4))
        else:
            pygame.draw.circle(surface, (255, 255, 0), (int(self.x - cam_x), int(self.y - cam_y)), 3)

class Enemy:
    def __init__(self, x, y, time_alive=0):
        self.x = x
        self.y = y
        self.speed = 80 + (time_alive)
        self.hp = 2
        self.angle = 0
        self.frame_idx = 0
        self.anim_timer = 0
        self.is_faster = False
        self.death_timer = -1
        
        w1 = load_and_scale(asset_path(ASSET_ENEMY_W1), 32, 32)
        w2 = load_and_scale(asset_path(ASSET_ENEMY_W2), 32, 32)
        h1 = load_and_scale(asset_path(ASSET_ENEMY_H1), 32, 32)
        h2 = load_and_scale(asset_path(ASSET_ENEMY_H2), 32, 32)
        
        self.frames_normal = [w1, w2] if w1 and w2 else [None, None]
        self.frames_hit = [h1, h2] if h1 and h2 else [None, None]
        self.frames = self.frames_normal
        self.rect = pygame.Rect(x - 16, y - 16, 32, 32)
        self.hit_timer=-1
        self.offscreen_time=0
        self.evolved=False

    def take_damage(self):
        self.hp -= 1
        if self.hp <= 0:
            self.death_timer = 3.0
            self.speed = 0
        elif self.hp == 1:
            self.speed *= 0.5
            self.frames = self.frames_hit

    def update(self, dt, player_x, player_y):
        if self.death_timer > 0:
            self.death_timer -= dt
            return
        
        if not self.is_faster and self.offscreen_time >= 2:
            self.is_faster = True
            self.speed *= 3

        dx = player_x - self.x
        dy = player_y - self.y
        target_angle = math.degrees(math.atan2(dy, dx))
        diff=((target_angle-self.angle+180)%360)-180
        self.angle += diff*min(1,dt*8)
        
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt
        self.rect.center = (self.x, self.y)
        
        self.anim_timer += dt
        if self.anim_timer > 0.25:
            self.anim_timer = 0
            self.frame_idx = 1 - self.frame_idx

    def draw(self, surface, cam_x, cam_y):
        img = self.frames[self.frame_idx]
        if img:
            rotated = pygame.transform.rotate(img, -self.angle)
            new_rect = rotated.get_rect(center=(self.x - cam_x, self.y - cam_y))
            surface.blit(rotated, new_rect.topleft)
        else:
            color = (0, 255, 0) if self.hp > 1 else (255, 128, 0)
            pygame.draw.rect(surface, color, (self.x - cam_x - 12, self.y - cam_y - 12, 24, 24))

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 300
        self.shoot_cd = 0
        self.angle = 0
        self.ammo = 12
        self.is_reloading = False
        self.reload_timer = 0
        self.image = load_and_scale(asset_path(ASSET_PLAYER), 48, 48)
        self.rect = pygame.Rect(x - 24, y - 24, 48, 24)

    def update(self, dt, keys, mx, my, cam_x, cam_y, bullets):
        if keys[pygame.K_w]: self.y -= self.speed * dt
        if keys[pygame.K_s]: self.y += self.speed * dt
        if keys[pygame.K_a]: self.x -= self.speed * dt
        if keys[pygame.K_d]: self.x += self.speed * dt
        
        self.rect.center = (self.x, self.y)
        world_mx = mx + cam_x
        world_my = my + cam_y
        
        dx = world_mx - self.x
        dy = world_my - self.y
        target_angle = math.degrees(math.atan2(dy, dx))
        diff=((target_angle-self.angle+180)%360)-180
        self.angle += diff*min(1,dt*4)
        
        if self.is_reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.ammo = 12
                self.is_reloading = False
        else:
            if keys[pygame.K_r] and self.ammo < 12:
                self.is_reloading = True
                self.reload_timer = 1.0 
                
            self.shoot_cd -= dt
            if pygame.mouse.get_pressed()[0] and self.shoot_cd <= 0 and self.ammo > 0:
                self.shoot_cd = 0.2
                self.ammo -= 1
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0:
                    bullets.append(Bullet(self.x, self.y, dx / dist, dy / dist))
            elif pygame.mouse.get_pressed()[0] and self.ammo==0:
                self.is_reloading = True
                self.reload_timer = 1.0 

    def draw(self, surface, cam_x, cam_y):
        if self.image:
            rotated = pygame.transform.rotate(self.image, -self.angle)
            new_rect = rotated.get_rect(center=(self.x - cam_x, self.y - cam_y))
            surface.blit(rotated, new_rect.topleft)
        else:
            pygame.draw.circle(surface, (255, 0, 0), (int(self.x - cam_x), int(self.y - cam_y)), 14)
            end_x = self.x - cam_x + math.cos(math.radians(self.angle)) * 40
            end_y = self.y - cam_y + math.sin(math.radians(self.angle)) * 40
            pygame.draw.line(surface, (255, 255, 255), (self.x - cam_x, self.y - cam_y), (end_x, end_y))

def draw_text(surface, text, x, y, size, color, anchor='center'):
    font = pygame.font.Font(None, size)
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    setattr(rect, anchor, (x, y))
    surface.blit(rendered, rect)

def rebuild_renderer(screen):
    sw, sh = screen.get_size()
    rw, rh = sw, sh
    display = pygame.Surface((rw, rh))
    night = pygame.Surface((rw, rh), pygame.SRCALPHA)
    night.fill((0, 0, 20, 160))
    return display, night

def main():
    pygame.init()
    played="none"
    VIRTUAL_W, VIRTUAL_H = 800, 600
    screen = pygame.display.set_mode((VIRTUAL_W, VIRTUAL_H), pygame.RESIZABLE)
    display_surface, night_overlay = rebuild_renderer(screen)
    pygame.display.set_caption(GAME_TITLE)
    pygame.display.set_icon(icon)
    clock = pygame.time.Clock()
    sw, sh = screen.get_size()
    
    bg_img = None
    try:
        raw_bg = pygame.image.load(asset_path(ASSET_GROUND)).convert()
        bg_img = pygame.Surface((128, 128))
        bg_img.blit(raw_bg, (0, 0))
    except Exception:
        pass

    state = "MENU"
    prev_state = "MENU"
    settings_idx = 0
    player = Player(400, 300)
    bullets, enemies = [], []
    score, spawn_timer = 0, 0
    cam_x, cam_y = 0, 0
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                    
                if state == "MENU":
                    if event.key == pygame.K_SPACE:
                        state = "GAME"
                        player = Player(400, 300)
                        bullets, enemies = [], []
                        score, spawn_timer = 0, 0
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                elif state == "GAME":
                    if event.key == pygame.K_ESCAPE:
                        state = "MENU"
                    elif event.key == pygame.K_p:
                        state = "PAUSE"
                elif state == "PAUSE":
                    if event.key == pygame.K_p:
                        state = "GAME"
                    elif event.key == pygame.K_ESCAPE:
                        state = "MENU"
                elif state == "GAMEOVER":
                    if event.key == pygame.K_SPACE:
                        state = "GAME"
                        player = Player(400, 300)
                        bullets, enemies = [], []
                        score, spawn_timer = 0, 0
                    elif event.key == pygame.K_ESCAPE:
                        state = "MENU"

        keys = pygame.key.get_pressed()
        raw_mx, raw_my = pygame.mouse.get_pos()
        
        render_w = display_surface.get_width()
        render_h = display_surface.get_height()
        screen_w, screen_h = screen.get_size()
        mx = raw_mx * render_w / screen_w
        my = raw_my * render_h / screen_h

        is_night = False

        if state == "GAME":
            if played != "none":
                played="none"
            player.update(dt, keys, mx, my, cam_x, cam_y, bullets)
            cam_x = player.x - render_w / 2
            cam_y = player.y - render_h / 2

            score += dt
            spawn_timer += dt
            
            cycle_time = score % 40
            is_night = cycle_time >= 30
            
            base_spawn = max(0.4, 2.0 - (score / 60.0))
            current_spawn_interval = base_spawn / 2 if is_night else base_spawn
            
            if spawn_timer > current_spawn_interval:
                spawn_timer = 0
                side = random.choice(['top', 'bottom', 'left', 'right'])
                if side == 'top': ex, ey = random.uniform(cam_x, cam_x + render_w), cam_y - 40
                elif side == 'bottom': ex, ey = random.uniform(cam_x, cam_x + render_w), cam_y + render_h + 40
                elif side == 'left': ex, ey = cam_x - 40, random.uniform(cam_y, cam_y + render_h)
                else: ex, ey = cam_x + render_w + 40, random.uniform(cam_y, cam_y + render_h)
                enemies.append(Enemy(ex, ey, time_alive=score))

            for b in bullets[:]:
                b.update(dt)
                if b.life <= 0: bullets.remove(b)

            for e in enemies[:]:
                e.update(dt, player.x, player.y)
                onscreen=(-32<=e.x-cam_x<=render_w+32 and -32<=e.y-cam_y<=render_h+32)
                if e.death_timer > 0:
                    continue
                elif e.death_timer != -1 and e.death_timer <= 0:
                    enemies.remove(e)
                    continue
                if e.hit_timer>0:
                    pass
                elif not onscreen:
                    e.offscreen_time+=dt
                    if e.offscreen_time>=2 and not e.evolved:
                        e.speed*=2
                        e.evolved=True
                else:
                    e.offscreen_time=0
                if e.hit_timer<=0 and e.hit_timer!=-1:
                    enemies.remove(e)
                    continue
                dist = math.sqrt((e.x - player.x)**2 + (e.y - player.y)**2)
                if dist < 26:
                    state = "GAMEOVER"

            for b in bullets[:]:
                for e in enemies[:]:
                    if b.rect.colliderect(e.rect):
                        e.take_damage()
                        if e.hp <= 0 and e in enemies: enemies.remove(e)
                        if b in bullets: bullets.remove(b)
                        break

        display_surface.fill((0, 0, 50) if not bg_img else (0, 0, 0))

        if state in ("GAME", "PAUSE", "GAMEOVER"):
            if bg_img:
                start_x = -int(cam_x % 128)
                start_y = -int(cam_y % 128)
                for tx in range(start_x, render_w + 128, 128):
                    for ty in range(start_y, render_h + 128, 128):
                        display_surface.blit(bg_img, (tx, ty))
            
            for b in bullets: b.draw(display_surface, cam_x, cam_y)
            for e in enemies: e.draw(display_surface, cam_x, cam_y)
            player.draw(display_surface, cam_x, cam_y)
            
            if is_night or (state == "PAUSE" and (score % 40) >= 30):
                display_surface.blit(night_overlay, (0, 0))
            
            draw_text(display_surface, f"Time Alive: {score:.0f}s", 10, 10, 36, (255, 255, 255), 'topleft')
            
            phase_text = "NIGHT" if is_night else "DAY"
            phase_color = (150, 150, 255) if is_night else (255, 255, 100)
            draw_text(display_surface, f"[{phase_text}]", VIRTUAL_W // 2, 20, 36, phase_color, 'center')
            
            ammo_text = "Reloading..." if player.is_reloading else f"Ammo: {player.ammo} / 12"
            ammo_color = (255, 0, 0) if player.ammo == 0 or player.is_reloading else (255, 255, 255)
            draw_text(display_surface, ammo_text, 10, 50, 36, ammo_color, 'topleft')

        if state == "MENU":
            display_surface.fill((20, 20, 25))
            draw_text(display_surface, BRAND_LOGO_TEXT, VIRTUAL_W // 2, VIRTUAL_H // 2 - 120, 24, (100, 200, 255))
            draw_text(display_surface, GAME_TITLE, VIRTUAL_W // 2, VIRTUAL_H // 2 - 60, 72, (255, 255, 255))
            draw_text(display_surface, "Press SPACE to Start", VIRTUAL_W // 2, VIRTUAL_H // 2 + 20, 36, (255, 255, 0))
            draw_text(display_surface, "WASD: Move  |  Mouse: Aim  |  Click: Shoot  |  R: Reload", VIRTUAL_W // 2, VIRTUAL_H - 70, 20, (150, 150, 150))
            draw_text(display_surface, "Copyright (c) 2026 fligma", VIRTUAL_W // 2, VIRTUAL_H - 40, 20, (150, 150, 150))
        elif state == "PAUSE":
            s = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            display_surface.blit(s, (0, 0))
            draw_text(display_surface, "PAUSED", VIRTUAL_W // 2, VIRTUAL_H // 2 - 20, 64, (255, 255, 255))
            draw_text(display_surface, "P: Resume | ESC: Menu", VIRTUAL_W // 2, VIRTUAL_H // 2 + 30, 28, (255, 255, 255))
        elif state == "GAMEOVER":
            if played=="none":
                MUSIC_GAMEOVER.play()
                played="GAMEOVER"
            s = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
            s.fill((0, 0, 0, 128))
            display_surface.blit(s, (0, 0))
            draw_text(display_surface, "GAME OVER", VIRTUAL_W // 2, VIRTUAL_H // 2 - 20, 64, (255, 0, 0))
            draw_text(display_surface, "SPACE: Restart  |  ESC: Menu", VIRTUAL_W // 2, VIRTUAL_H // 2 + 30, 28, (255, 255, 255))

        scaled_surface = pygame.transform.scale(display_surface, screen.get_size())
            
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()