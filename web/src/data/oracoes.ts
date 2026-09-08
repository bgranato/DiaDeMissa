/**
 * Catálogo de orações católicas tradicionais.
 *
 * Ordem das categorias = ordem de exibição na tela.
 * "rosario" primeiro porque é a base do que o usuário pediu.
 */

export type CategoriaOracao = 'rosario' | 'mariana' | 'cotidiana' | 'devocional'

export interface Oracao {
  id: string
  nome: string
  categoria: CategoriaOracao
  texto: string
  observacao?: string
}

export const CATEGORIAS: { id: CategoriaOracao; nome: string; descricao: string }[] = [
  { id: 'rosario', nome: 'Rosário', descricao: 'Orações utilizadas na reza do Santo Rosário' },
  { id: 'mariana', nome: 'Orações Marianas', descricao: 'Em honra a Nossa Senhora' },
  { id: 'cotidiana', nome: 'Orações Cotidianas', descricao: 'Para o dia a dia' },
  { id: 'devocional', nome: 'Devocionais', descricao: 'Tradicionais e populares' },
]

export const ORACOES: Oracao[] = [
  // ===== ROSÁRIO =====
  {
    id: 'sinal-da-cruz',
    nome: 'Sinal da Cruz',
    categoria: 'rosario',
    texto: 'Em nome do Pai, e do Filho, e do Espírito Santo.\nAmém.',
  },
  {
    id: 'credo',
    nome: 'Credo (Símbolo dos Apóstolos)',
    categoria: 'rosario',
    texto:
`Creio em Deus Pai todo-poderoso, Criador do céu e da terra;
e em Jesus Cristo, seu único Filho, Nosso Senhor,
que foi concebido pelo poder do Espírito Santo;
nasceu da Virgem Maria;
padeceu sob Pôncio Pilatos, foi crucificado, morto e sepultado.
Desceu à mansão dos mortos;
ressuscitou ao terceiro dia;
subiu aos céus;
está sentado à direita de Deus Pai todo-poderoso,
donde há de vir a julgar os vivos e os mortos.
Creio no Espírito Santo;
na Santa Igreja Católica;
na comunhão dos santos;
na remissão dos pecados;
na ressurreição da carne;
na vida eterna. Amém.`,
  },
  {
    id: 'pai-nosso',
    nome: 'Pai-Nosso',
    categoria: 'rosario',
    texto:
`Pai nosso que estais nos céus,
santificado seja o vosso nome;
venha a nós o vosso Reino;
seja feita a vossa vontade,
assim na terra como no céu.
O pão nosso de cada dia nos dai hoje;
perdoai-nos as nossas ofensas,
assim como nós perdoamos a quem nos tem ofendido;
e não nos deixeis cair em tentação,
mas livrai-nos do mal. Amém.`,
  },
  {
    id: 'ave-maria',
    nome: 'Ave-Maria',
    categoria: 'rosario',
    texto:
`Ave Maria, cheia de graça, o Senhor é convosco.
Bendita sois vós entre as mulheres,
e bendito é o fruto do vosso ventre, Jesus.
Santa Maria, Mãe de Deus, rogai por nós, pecadores,
agora e na hora da nossa morte. Amém.`,
  },
  {
    id: 'gloria-ao-pai',
    nome: 'Glória ao Pai',
    categoria: 'rosario',
    texto:
`Glória ao Pai, ao Filho e ao Espírito Santo.
Como era no princípio, agora e sempre. Amém.`,
  },
  {
    id: 'oracao-de-fatima',
    nome: 'Oração de Fátima (Ó meu Jesus)',
    categoria: 'rosario',
    texto:
`Ó meu Jesus, perdoai-nos e livrai-nos do fogo do inferno;
levai as almas todas para o Céu,
e socorrei principalmente as que mais precisarem da Vossa misericórdia. Amém.`,
    observacao: 'Rezada após cada dezena, conforme pedido de Nossa Senhora em Fátima.',
  },
  {
    id: 'oracao-do-anjo',
    nome: 'Oração do Anjo (Oração da Paz)',
    categoria: 'rosario',
    texto:
`Meu Deus, eu creio, adoro, espero e amo-Vos. Peço-Vos perdão para os que não crêem, não adoram, não esperam e não Vos amam. Amém.`,
    observacao: 'Ensinada pelo Anjo de Portugal (Anjo da Paz) aos pastorinhos de Fátima em 1916.',
  },
  {
    id: 'salve-rainha',
    nome: 'Salve-Rainha',
    categoria: 'rosario',
    texto:
`Salve, Rainha, Mãe de misericórdia,
vida, doçura e esperança nossa, salve!
A vós bradamos, os degredados filhos de Eva.
A vós suspiramos, gemendo e chorando neste vale de lágrimas.
Eia, pois, advogada nossa,
esses vossos olhos misericordiosos a nós volvei;
e depois deste desterro, mostrai-nos Jesus, bendito fruto do vosso ventre.
Ó clemente, ó piedosa, ó doce sempre Virgem Maria.
Rogai por nós, Santa Mãe de Deus,
para que sejamos dignos das promessas de Cristo. Amém.`,
  },
  {
    id: 'oferecimento-rosario',
    nome: 'Oferecimento do Rosário',
    categoria: 'rosario',
    texto:
`Divino Jesus, nós Vos oferecemos este Rosário que vamos rezar,
contemplando os mistérios da nossa redenção.
Concedei-nos, por intercessão da Virgem Maria, Mãe de Deus e nossa Mãe,
as virtudes de que necessitamos para bem rezá-lo
e a graça de ganharmos as indulgências desta santa devoção. Amém.`,
  },

  // ===== MARIANAS =====
  {
    id: 'angelus',
    nome: 'Angelus (Anjo do Senhor)',
    categoria: 'mariana',
    texto:
`V. O Anjo do Senhor anunciou a Maria.
R. E ela concebeu do Espírito Santo.
Ave Maria...

V. Eis aqui a serva do Senhor.
R. Faça-se em mim segundo a vossa palavra.
Ave Maria...

V. E o Verbo se fez carne.
R. E habitou entre nós.
Ave Maria...

V. Rogai por nós, Santa Mãe de Deus.
R. Para que sejamos dignos das promessas de Cristo.

Oremos: Infundi, Senhor, a vossa graça em nossos corações,
para que, conhecendo, pela mensagem do Anjo, a Encarnação de Cristo, vosso Filho,
cheguemos, por sua paixão e cruz, à glória da ressurreição.
Pelo mesmo Cristo, nosso Senhor. Amém.`,
    observacao: 'Rezado tradicionalmente às 6h, 12h e 18h.',
  },
  {
    id: 'regina-caeli',
    nome: 'Rainha do Céu (Regina Caeli)',
    categoria: 'mariana',
    texto:
`Rainha do Céu, alegrai-vos, aleluia!
Porque Aquele que merecestes trazer em vosso seio, aleluia!
Ressuscitou como disse, aleluia!
Rogai por nós a Deus, aleluia!

V. Alegrai-vos e exultai, ó Virgem Maria, aleluia!
R. Porque o Senhor ressuscitou verdadeiramente, aleluia!

Oremos: Ó Deus, que vos dignastes alegrar o mundo
com a ressurreição do vosso Filho, nosso Senhor Jesus Cristo,
concedei-nos, vos pedimos, que, pela sua Mãe, a Virgem Maria,
alcancemos as alegrias da vida eterna. Por Cristo, nosso Senhor. Amém.`,
    observacao: 'Substitui o Angelus durante o Tempo Pascal.',
  },
  {
    id: 'memorare',
    nome: 'Memorare (Lembrai-vos)',
    categoria: 'mariana',
    texto:
`Lembrai-vos, ó piíssima Virgem Maria,
que nunca se ouviu dizer que algum daqueles que recorreram à vossa proteção,
implorando o vosso auxílio, e reclamando o vosso socorro,
fosse por vós desamparado.
Animado eu, pois, de igual confiança,
a vós, ó Virgem entre todas singular, como a Mãe recorro,
de vós me valho, e gemendo sob o peso dos meus pecados, me prostro a vossos pés.
Não desprezeis as minhas súplicas, ó Mãe do Filho de Deus humanado,
mas dignai-vos de ouvi-las propícia, e de me alcançar o que vos rogo. Amém.`,
    observacao: 'Atribuída a São Bernardo de Claraval.',
  },
  {
    id: 'sub-tuum-praesidium',
    nome: 'À Vossa Proteção (Sub Tuum Praesidium)',
    categoria: 'mariana',
    texto:
`À vossa proteção recorremos, Santa Mãe de Deus.
Não desprezeis as nossas súplicas em nossas necessidades,
mas livrai-nos sempre de todos os perigos,
ó Virgem gloriosa e bendita. Amém.`,
    observacao: 'A oração mariana mais antiga conhecida (século III).',
  },
  {
    id: 'bendito-louvado-seja',
    nome: 'Bendito e Louvado Seja',
    categoria: 'mariana',
    texto:
`Bendito e louvado seja Nosso Senhor Jesus Cristo no Santíssimo Sacramento do Altar,
e Maria Santíssima concebida sem pecado original. Amém.`,
  },

  // ===== COTIDIANAS =====
  {
    id: 'antes-refeicao',
    nome: 'Antes das Refeições',
    categoria: 'cotidiana',
    texto:
`Abençoai-nos, Senhor, e a estes alimentos
que, por vossa bondade, vamos receber.
Por Cristo, nosso Senhor. Amém.`,
  },
  {
    id: 'apos-refeicao',
    nome: 'Após as Refeições',
    categoria: 'cotidiana',
    texto:
`Nós vos damos graças, Senhor onipotente,
por estes e todos os benefícios recebidos da vossa bondade.
Vós, que viveis e reinais pelos séculos dos séculos. Amém.`,
  },
  {
    id: 'oferecimento-dia',
    nome: 'Oferecimento do Dia',
    categoria: 'cotidiana',
    texto:
`Coração Divino de Jesus,
eu vos ofereço, por meio do Coração Imaculado de Maria,
em união com o Santo Sacrifício da Missa,
as minhas orações, ações, alegrias e sofrimentos deste dia,
em reparação das nossas ofensas
e pelas intenções do Sumo Pontífice neste mês. Amém.`,
    observacao: 'Apostolado da Oração — feito ao despertar.',
  },
  {
    id: 'ato-de-contricao',
    nome: 'Ato de Contrição',
    categoria: 'cotidiana',
    texto:
`Meu Deus, eu me arrependo de todo o coração de todos os meus pecados
e os detesto, por temer o castigo do inferno e a perda do céu,
mas, sobretudo, por terem ofendido a Vós, meu Deus, infinitamente bom
e digno de todo o meu amor.
Proponho firmemente, com o auxílio da vossa divina graça,
nunca mais Vos ofender e fugir das ocasiões próximas de pecado. Amém.`,
  },
  {
    id: 'oracao-anjo-da-guarda',
    nome: 'Oração ao Anjo da Guarda',
    categoria: 'cotidiana',
    texto:
`Santo Anjo do Senhor, meu zeloso guardador,
se a ti me confiou a piedade divina, sempre me rege, me guarde, me governe e ilumine. Amém.`,
  },

  // ===== DEVOCIONAIS =====
  {
    id: 'sao-miguel-arcanjo',
    nome: 'Oração a São Miguel Arcanjo',
    categoria: 'devocional',
    texto:
`São Miguel Arcanjo, defendei-nos no combate,
sede o nosso refúgio contra a maldade e as ciladas do demônio.
Ordene-lhe Deus, instantemente o pedimos,
e vós, Príncipe da milícia celeste,
pela virtude divina, precipitai no inferno a Satanás
e aos outros espíritos malignos que andam pelo mundo
para perder as almas. Amém.`,
    observacao: 'Composta pelo Papa Leão XIII em 1886.',
  },
  {
    id: 'vinde-espirito-santo',
    nome: 'Vinde, Espírito Santo',
    categoria: 'devocional',
    texto:
`Vinde, Espírito Santo, enchei os corações dos vossos fiéis
e acendei neles o fogo do vosso amor.

V. Enviai o vosso Espírito e tudo será criado.
R. E renovareis a face da terra.

Oremos: Ó Deus, que instruístes os corações dos vossos fiéis
com a luz do Espírito Santo, fazei que apreciemos retamente todas as coisas
segundo o mesmo Espírito e gozemos sempre de sua consolação.
Por Cristo, nosso Senhor. Amém.`,
  },
  {
    id: 'alma-de-cristo',
    nome: 'Alma de Cristo (Anima Christi)',
    categoria: 'devocional',
    texto:
`Alma de Cristo, santificai-me.
Corpo de Cristo, salvai-me.
Sangue de Cristo, inebriai-me.
Água do lado de Cristo, lavai-me.
Paixão de Cristo, confortai-me.
Ó bom Jesus, ouvi-me.
Dentro de vossas chagas, escondei-me.
Não permitais que eu me separe de Vós.
Do espírito maligno, defendei-me.
Na hora da minha morte, chamai-me.
E mandai-me ir para Vós,
para que com os vossos santos vos louve,
pelos séculos dos séculos. Amém.`,
  },
  {
    id: 'pai-eterno',
    nome: 'Oração ao Pai Eterno',
    categoria: 'devocional',
    texto:
`Eterno Pai, eu vos ofereço o Corpo e Sangue, Alma e Divindade
de vosso diletíssimo Filho, Nosso Senhor Jesus Cristo,
em expiação dos nossos pecados e os do mundo inteiro.

Pela sua dolorosa Paixão, tende misericórdia de nós e do mundo inteiro.

Santo Deus, Santo Forte, Santo Imortal, tende piedade de nós e do mundo inteiro.`,
    observacao: 'Terço da Misericórdia — rezado às 15h, hora da Misericórdia.',
  },
]

export const ORACOES_POR_CATEGORIA: Record<CategoriaOracao, Oracao[]> = ORACOES.reduce(
  (acc, o) => {
    if (!acc[o.categoria]) acc[o.categoria] = []
    acc[o.categoria].push(o)
    return acc
  },
  {} as Record<CategoriaOracao, Oracao[]>,
)
