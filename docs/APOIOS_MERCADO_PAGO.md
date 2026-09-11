# Apoio voluntário via Mercado Pago

O apoio é **avulso e opcional**. O Dia de Missa nunca recebe nem armazena
dados de cartão, Pix, CPF ou payloads de pagamento: o pagamento acontece no
Checkout Pro hospedado pelo Mercado Pago.

## Antes de ativar em produção

1. No painel do Mercado Pago, crie (ou selecione) a aplicação de produção e
   habilite o Checkout Pro com Pix e cartão.
2. Em `Webhooks`, cadastre o tópico **Pagamentos** para:
   `https://diademissa.com.br/api/v1/apoios/mercadopago/webhook`
3. Copie o *Access token* de produção e a chave secreta de assinatura do
   webhook para o arquivo de ambiente **somente no servidor**:

   ```env
   APP_BASE_URL=https://diademissa.com.br
   MERCADOPAGO_ACCESS_TOKEN=...
   MERCADOPAGO_WEBHOOK_SECRET=...
   APOIOS_ATIVOS=true
   ```

4. Reinicie a API e abra uma missa até a tela final. A oferta só aparece
   quando as três configurações acima estão presentes.
5. Faça primeiro um pagamento de teste autorizado pelo Mercado Pago e confira
   o registro de webhook. Só um webhook com assinatura válida, seguido da
   consulta do pagamento na API oficial, pode marcar um apoio como `approved`.

Não envie tokens pelo chat, por e-mail, para o Git ou para variáveis `VITE_*`.

## Regras de segurança e produto

- Valores fechados no servidor: R$ 5, R$ 10 e R$ 15; moeda BRL; sem recorrência.
- O frontend recebe somente uma URL HTTPS do Checkout Pro.
- A confirmação compara referência opaca, valor e moeda antes de registrar o
  resultado do provedor.
- O pedido aparece apenas no fim da missa e pode ser dispensado. Ao dispensar,
  o navegador espera 30 dias antes de voltar a mostrá-lo.
- Se a configuração falhar, a missa continua normalmente e a oferta não aparece.

Referências oficiais: [Checkout Pro](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro/overview)
e [Webhooks](https://www.mercadopago.com.br/developers/pt/docs/your-integrations/notifications/webhooks).
