function replaceArena(html) {
    const documentFragment = new DOMParser().parseFromString(html, 'text/html');
    const newArena = documentFragment.querySelector('.arena');
    const currentArena = document.querySelector('.arena');

    if (!newArena || !currentArena) {
        throw new Error('The server returned an invalid game view.');
    }

    currentArena.replaceWith(newArena);
}

async function submitGuess(form, submitter) {
    const buttons = form.querySelectorAll('button');
    buttons.forEach((button) => {
        button.disabled = true;
    });

    const formData = new FormData(form);
    formData.set('guess', submitter.value);

    const response = await fetch(form.action, {
        method: 'POST',
        headers: {'X-Requested-With': 'fetch'},
        body: formData
    });

    if (!response.ok) {
        throw new Error('The answer could not be submitted.');
    }

    replaceArena(await response.text());
}

async function loadNextMatchup(form) {
    const response = await fetch(form.action, {
        headers: {'X-Requested-With': 'fetch'}
    });

    if (!response.ok) {
        throw new Error('The next matchup could not be loaded.');
    }

    replaceArena(await response.text());
}

document.addEventListener('submit', async (event) => {
    const form = event.target;

    if (form.matches('#guess-form')) {
        event.preventDefault();
        try {
            await submitGuess(form, event.submitter);
        } catch (error) {
            form.querySelectorAll('button').forEach((button) => {
                button.disabled = false;
            });
            window.alert(error.message);
        }
    } else if (form.matches('.new-matchup-form')) {
        event.preventDefault();
        const button = form.querySelector('button');
        button.disabled = true;
        try {
            await loadNextMatchup(form);
        } catch (error) {
            button.disabled = false;
            window.alert(error.message);
        }
    }
});
