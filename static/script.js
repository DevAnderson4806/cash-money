// Função para confirmar a exclusão de uma transação
function confirmarExclusao(event) {
  if (!confirm("Você tem certeza que deseja excluir esta transação?")) {
    event.preventDefault(); // Cancela o envio do formulário se o usuário clicar em "Cancelar"
  }
}

// Validação do formulário
document.querySelector("form")?.addEventListener("submit", function (event) {
  const descricao = document.querySelector('input[name="descricao"]').value;
  const valor = document.querySelector('input[name="valor"]').value;

  if (!descricao || valor <= 0) {
    alert("Por favor, preencha todos os campos corretamente!");
    event.preventDefault();
  }
});

// Adicionar animação ao carregar a página
document.addEventListener("DOMContentLoaded", () => {
  document.body.style.opacity = 0;
  document.body.style.transition = "opacity 0.5s ease-in-out";
  document.body.style.opacity = 1;
});

document.addEventListener("DOMContentLoaded", () => {
  const userName = "Admin"; // Substituir pelo nome do usuário real vindo do backend
  const container = document.querySelector(".container");
  const welcomeMessage = document.createElement("p");
  welcomeMessage.textContent = `Olá, ${userName}! Seja bem-vindo ao painel.`;
  welcomeMessage.style.marginTop = "10px";
  container.prepend(welcomeMessage);
});
