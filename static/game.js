(() => {
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const animations = new Set();
    const status = document.querySelector('#game-status');
    const errorPanel = document.querySelector('#game-error');
    let pending = false;

    // Short synthesized cues need no downloads, decoder, or audio library.
    class RoundSound {
        constructor(button) {
            this.button = button;
            this.context = null;
            this.voices = new Set();
            this.generation = 0;
            this.enabled = false;
            this.AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!button || !this.AudioContext) return;

            try {
                this.enabled = localStorage.getItem('country-battle-sound') === 'on';
            } catch { /* Sound still works when storage is unavailable. */ }
            button.hidden = false;
            this.updateButton();
            button.addEventListener('click', () => {
                this.enabled = !this.enabled;
                try {
                    localStorage.setItem('country-battle-sound', this.enabled ? 'on' : 'off');
                } catch { /* Keep the preference for this page. */ }
                this.updateButton();
                if (this.enabled) this.play('select');
                else this.stop();
            });
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) this.stop();
            });
        }

        updateButton() {
            this.button.setAttribute('aria-pressed', String(this.enabled));
            this.button.title = `Turn sound effects ${this.enabled ? 'off' : 'on'}`;
            this.button.querySelector('span').textContent = this.enabled ? 'Sound on' : 'Sound off';
        }

        async play(cue, delay = 0) {
            if (!this.enabled || document.hidden || !this.AudioContext) return;
            const generation = this.generation;
            try {
                // Called by the initial click, before the game's first await.
                this.context ??= new this.AudioContext();
                if (this.context.state === 'suspended') await this.context.resume();
                if (!this.enabled || document.hidden || this.context.state !== 'running'
                    || generation !== this.generation) return;

                // Frequency, duration, offset, and gain; all cues stay quiet.
                const notes = {
                    select: [[640, .045, 0, .035]],
                    next: [[440, .06, 0, .022], [660, .07, .045, .022]],
                    correct: [[660, .11, 0, .035], [880, .12, .075, .03], [1100, .14, .15, .025]],
                    incorrect: [[220, .14, 0, .028], [165, .15, .08, .02]],
                };
                const start = this.context.currentTime + delay;
                for (const [frequency, duration, offset, volume] of notes[cue] || []) {
                    const oscillator = this.context.createOscillator();
                    const envelope = this.context.createGain();
                    const at = start + offset;
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(frequency, at);
                    envelope.gain.setValueAtTime(.0001, at);
                    envelope.gain.linearRampToValueAtTime(volume, at + .006);
                    envelope.gain.exponentialRampToValueAtTime(.0001, at + duration);
                    oscillator.connect(envelope);
                    envelope.connect(this.context.destination);
                    this.voices.add(oscillator);
                    oscillator.onended = () => {
                        this.voices.delete(oscillator);
                        oscillator.disconnect();
                        envelope.disconnect();
                    };
                    oscillator.start(at);
                    oscillator.stop(at + duration);
                }
            } catch {
                // A blocked or unavailable audio device must never hold up a round.
                this.stop();
            }
        }

        stop() {
            this.generation += 1;
            for (const voice of this.voices) {
                try { voice.stop(); } catch { /* Already stopped. */ }
            }
            this.voices.clear();
        }
    }

    const sound = new RoundSound(document.querySelector('#sound-toggle'));

    function animate(element, keyframes, options = {}) {
        if (!element?.animate || motionPreference.matches) return Promise.resolve();
        try {
            const animation = element.animate(keyframes, {
                duration: 260,
                easing: 'cubic-bezier(.2, .8, .2, 1)',
                fill: 'backwards',
                ...options,
            });
            animations.add(animation);
            return animation.finished.catch(() => {}).finally(() => {
                animations.delete(animation);
                animation.cancel();
            });
        } catch {
            return Promise.resolve();
        }
    }

    motionPreference.addEventListener('change', () => {
        if (motionPreference.matches) {
            for (const animation of animations) animation.cancel();
        }
    });

    function revealArena(arena, kind, previousStreak) {
        const effects = [];
        const rise = [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }];
        if (kind === 'next') {
            arena.querySelectorAll('.contender').forEach((card, index) => {
                effects.push(animate(card, rise, { duration: 240, delay: index * 45 }));
            });
            effects.push(animate(arena.querySelector('.versus'), [{ opacity: 0 }, { opacity: 1 }], { delay: 70 }));
        } else {
            arena.querySelectorAll('.country-stat dd').forEach((stat, index) => {
                effects.push(animate(stat, rise, { delay: (index % 2) * 65 }));
            });
            arena.querySelectorAll('.contender-score, .round-standing').forEach((element) => {
                effects.push(animate(element, rise, { delay: 100 }));
            });
            effects.push(animate(arena.querySelector('.result-message'), rise, { delay: 120 }));
            effects.push(animate(arena.querySelector('.new-matchup-button'), rise, { delay: 150 }));
            effects.push(animate(arena.querySelector('.contender--winner .country-flag'), [
                { transform: 'scale(.96)' }, { transform: 'scale(1.06)', offset: .5 }, { transform: 'scale(1)' },
            ], { duration: 320, delay: 90 }));
            if (Number(arena.dataset.streak) > previousStreak) {
                effects.push(animate(arena.querySelector('.streak-number'), [
                    { transform: 'scale(1)' }, { transform: 'scale(1.24)', offset: .4 }, { transform: 'scale(1)' },
                ], { duration: 300, delay: 100 }));
            }
        }
        return Promise.all(effects);
    }

    async function readArena(response, kind) {
        if (!response.ok) {
            let message = kind === 'guess'
                ? "We couldn't confirm your answer. You can load a new matchup below."
                : "The next matchup couldn't be loaded. Please try again.";
            if (response.headers.get('Content-Type')?.includes('application/json')) {
                const payload = await response.json().catch(() => null);
                if (typeof payload?.errors?.form === 'string') message = payload.errors.form;
            }
            throw new Error(message);
        }
        const page = new DOMParser().parseFromString(await response.text(), 'text/html');
        const arena = page.querySelector('.arena');
        const answered = ['correct', 'incorrect'].includes(arena?.dataset.result);
        if (!arena || (kind === 'guess' ? !answered : answered)
            || !arena.querySelector(kind === 'guess' ? '.result-message' : '#guess-form')) {
            throw new Error('The game returned an incomplete round. Please load a new matchup.');
        }
        return arena;
    }

    async function playRound(form, submitter, kind) {
        if (pending) return;
        let arena = document.querySelector('.arena');
        if (!arena) return;
        if (kind === 'guess' && !['country1', 'country2', 'draw'].includes(submitter?.value)) return;

        pending = true;
        const previousStreak = Number(arena.dataset.streak) || 0;
        const focusWasInRound = arena.contains(document.activeElement) || form.contains(document.activeElement);
        // form.elements also includes the draw button outside the form's DOM subtree.
        const buttons = Array.from(form.elements).filter((element) => element.tagName === 'BUTTON');
        const body = kind === 'guess' ? new FormData(form) : null;
        if (body) body.set('guess', submitter.value);
        buttons.forEach((button) => { button.disabled = true; });
        arena.setAttribute('aria-busy', 'true');
        arena.dataset.phase = kind === 'guess' ? 'submitting' : 'loading';
        submitter?.closest('.contender')?.classList.add('contender--pending');
        errorPanel.hidden = true;
        status.textContent = kind === 'guess' ? 'Checking your call…' : 'Loading the next matchup…';
        sound.play(kind === 'guess' ? 'select' : 'next');

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);
        try {
            const response = await fetch(form.action, {
                method: kind === 'guess' ? 'POST' : 'GET',
                headers: { 'X-Requested-With': 'fetch' },
                cache: 'no-store',
                body,
                signal: controller.signal,
            });
            const nextArena = await readArena(response, kind);
            clearTimeout(timeout);
            const shouldFocus = arena.contains(document.activeElement) || form.contains(document.activeElement)
                || (focusWasInRound && document.activeElement === document.body);
            arena.replaceWith(nextArena);
            arena = nextArena;
            arena.setAttribute('aria-busy', 'true');
            arena.dataset.phase = kind === 'guess' ? 'revealing' : 'entering';
            if (kind === 'next' && shouldFocus && arena.getBoundingClientRect().top < 0) {
                arena.scrollIntoView({ behavior: motionPreference.matches ? 'auto' : 'smooth', block: 'start' });
            }
            if (kind === 'guess') sound.play(arena.dataset.result, motionPreference.matches ? 0 : .12);
            await revealArena(arena, kind, previousStreak);
            status.textContent = kind === 'guess'
                ? `${arena.querySelector('.result-message').textContent.replace(/\s+/g, ' ').trim()} Current streak: ${arena.dataset.streak}.`
                : `New matchup: ${Array.from(arena.querySelectorAll('.country-name'), (name) => name.textContent).join(' versus ')}. Pick the winner.`;
            if (shouldFocus && document.activeElement === document.body) {
                const target = kind === 'guess' ? arena.querySelector('.new-matchup-button') : arena;
                target.focus({ preventScroll: true });
            }
        } catch (error) {
            status.textContent = '';
            document.querySelector('#game-error-message').textContent = error.name === 'AbortError' || error instanceof TypeError
                ? kind === 'guess'
                    ? "We couldn't confirm whether your answer was saved. Load a new matchup to continue."
                    : 'The connection was interrupted. Please try loading a new matchup.'
                : error.message;
            errorPanel.hidden = false;
            if (focusWasInRound && document.activeElement === document.body && submitter?.isConnected) {
                // Re-enable before restoring keyboard focus.
                submitter.disabled = false;
                submitter.focus({ preventScroll: true });
            }
        } finally {
            clearTimeout(timeout);
            buttons.forEach((button) => { button.disabled = false; });
            arena.removeAttribute('aria-busy');
            delete arena.dataset.phase;
            arena.querySelector('.contender--pending')?.classList.remove('contender--pending');
            pending = false;
        }
    }

    document.addEventListener('submit', (event) => {
        const form = event.target;
        const kind = form.matches('#guess-form') ? 'guess' : form.matches('.new-matchup-form') ? 'next' : null;
        if (!kind) return;
        event.preventDefault();
        void playRound(form, event.submitter, kind);
    });
})();
