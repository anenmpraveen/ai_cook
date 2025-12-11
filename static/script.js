function generateRecipe() {
    const ingredients = document.getElementById("ingredients").value.split(",");
    const cuisine = document.getElementById("cuisine").value;
    const difficulty = document.getElementById("difficulty").value;
    const servings = document.getElementById("servings").value;
    const time = document.getElementById("time").value;

    const requestData = {
        ingredients: ingredients.map(ing => ing.trim()),
        cuisine: cuisine,
        difficulty: difficulty,
        servings: servings,
        time: time
    };

    document.getElementById("loading").classList.remove("hidden");

    fetch("/generate-recipe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("loading").classList.add("hidden");

        if (data.error) {
            document.getElementById("recipe-text").innerText = "Error: " + data.error;
        } else {
            document.getElementById("recipe-text").innerHTML = data.recipe.replace(/\n/g, "<br>");
        }

        openModal();
    })
    .catch(error => {
        document.getElementById("loading").classList.add("hidden");
        document.getElementById("recipe-text").innerText = "Error fetching recipe.";
        console.error("Error fetching data:", error);
        openModal();
    });
}

function openModal() {
    const modal = document.getElementById("recipe-modal");
    modal.classList.remove("hidden");
    setTimeout(() => modal.querySelector(".modal").classList.add("show"), 10);
}

function closeModal() {
    const modal = document.getElementById("recipe-modal");
    if (!modal) {
        console.error("Modal element not found!");
        return;
    }

    const modalContent = modal.querySelector(".modal");
    if (modalContent) {
        modalContent.classList.remove("show");
    }

    setTimeout(() => {
        modal.classList.add("hidden");
    }, 300);
}


