import { Mass, UserReminder, HistoryItem } from '../types/mass';

export const MOCK_MASS: Mass = {
  id: '2026-05-10-mass',
  data: "2026-05-10",
  celebracao: "5º Domingo da Páscoa",
  tempo_liturgico: "Páscoa",
  resumo: "Jesus apresenta-se como a videira verdadeira e nós somos os ramos. Permanecer nele é essencial para dar frutos.",
  blocos: [
    {
      ordem: 1,
      tipo: "canto_entrada",
      titulo: "Canto de Entrada",
      conteudo: "Cristo ressuscitou, Aleluia! Venceu a morte com amor, Aleluia! \n\nO Senhor é nossa luz e nossa salvação. A quem temerei? O Senhor é o protetor de minha vida. De quem terei medo? \n\nQuando os malvados me atacam para me devorar, meus inimigos e adversários é que tropeçam e caem."
    },
    {
      ordem: 2,
      tipo: "ato_penitencial",
      titulo: "Ato Penitencial",
      conteudo: "Senhor, que subistes ao céu para nos preparar um lugar, tende piedade de nós. \n\nSenhor, tende piedade de nós. \n\nCristo, que estais à direita do Pai para interceder por nós, tende piedade de nós. \n\nCristo, tende piedade de nós."
    },
    {
      ordem: 3,
      tipo: "oracao_dia",
      titulo: "Oração do Dia",
      conteudo: "Ó Deus, que pela humilhação do vosso Filho levantastes o mundo decaído, dai aos vossos fiéis uma santa alegria, para que aqueles que libertastes da escravidão do pecado desfrutem da felicidade eterna. Por nosso Senhor Jesus Cristo, vosso Filho, na unidade do Espírito Santo."
    },
    {
      ordem: 4,
      tipo: "primeira_leitura",
      titulo: "Primeira Leitura",
      referencia: "At 13,14.43-52",
      conteudo: "Naqueles dias, Paulo e Barnabé, partindo de Perge, chegaram a Antioquia da Pisídia. No sábado, entraram na sinagoga e sentaram-se. \n\nMuitos judeus e prosélitos piedosos seguiram Paulo e Barnabé. Estes conversavam com eles, exortando-os a permanecerem fiéis à graça de Deus. No sábado seguinte, quase toda a cidade se reuniu para ouvir a palavra do Senhor."
    },
    {
      ordem: 5,
      tipo: "salmo_responsorial",
      titulo: "Salmo Responsorial",
      referencia: "Sl 99(100)",
      conteudo: "R. Sabei que o Senhor, só ele, é Deus, nós somos o seu povo e seu rebanho.\n\nAclamai o Senhor, ó terra inteira, servi ao Senhor com alegria, ide a ele com cantos de júbilo.\n\nSabei que o Senhor, só ele, é Deus, ele nos fez e a ele pertencemos, somos o seu povo e ovelhas de seu pasto."
    },
    {
      ordem: 6,
      tipo: "segunda_leitura",
      titulo: "Segunda Leitura",
      referencia: "Ap 7,9.14b-17",
      conteudo: "Eu, João, vi uma multidão imensa, que ninguém podia contar, de todas as nações, tribos, povos e línguas. Estavam de pé diante do trono e diante do Cordeiro, trajados com vestes brancas e com palmas na mão."
    },
    {
      ordem: 7,
      tipo: "evangelho",
      titulo: "Evangelho",
      referencia: "Jo 10,27-30",
      conteudo: "Naquele tempo, disse Jesus: 'As minhas ovelhas escutam a minha voz, eu as conheço e elas me seguem. Eu dou-lhes a vida eterna e elas jamais se perderão. Ninguém as vai arrancar da minha mão. \n\nMeu Pai, que mas deu, é maior do que todos; e ninguém as pode arrancar da mão do meu Pai. Eu e o Pai somos um'."
    },
    {
      ordem: 8,
      tipo: "comunhao",
      titulo: "Comunhão",
      conteudo: "Eu sou o pão vivo descido do céu; quem comer deste pão viverá eternamente. O pão que eu darei é a minha carne para a vida do mundo. \n\nPermanecei em mim e eu permanecerei em vós, diz o Senhor; quem permanece em mim dá muito fruto."
    },
    {
      ordem: 9,
      tipo: "bencao_final",
      titulo: "Bênção Final",
      conteudo: "O Senhor esteja convosco. \nEle está no meio de nós. \n\nAbençoe-vos Deus todo-poderoso, Pai e Filho e Espírito Santo. \nAmém. \n\nIde em paz e o Senhor vos acompanhe. \nGraças a Deus."
    }
  ]
};

export const MOCK_HISTORY: HistoryItem[] = [
  {
    id: 'h1',
    massId: '2026-05-09-mass',
    celebracao: 'Sábado da 4ª Semana da Páscoa',
    data: '2026-05-09',
    progresso: 100
  },
  {
    id: 'h2',
    massId: '2026-05-03-mass',
    celebracao: '4º Domingo da Páscoa',
    data: '2026-05-03',
    progresso: 45
  }
];

export const MOCK_REMINDERS: UserReminder[] = [
  {
    id: 'r1',
    horario: '08:00',
    celebracao: 'Missa Dominical',
    ativo: true,
    visto: false
  },
  {
    id: 'r2',
    horario: '18:30',
    celebracao: 'Missa Semanal',
    ativo: false,
    visto: true
  }
];

export const CALENDAR_MASSES = [
  { id: '1', data: '2026-05-11', celebracao: 'Segunda-feira da 5ª Semana da Páscoa', tempo: 'Páscoa' },
  { id: '2', data: '2026-05-12', celebracao: 'Terça-feira da 5ª Semana da Páscoa', tempo: 'Páscoa' },
  { id: '3', data: '2026-05-13', celebracao: 'Nossa Senhora de Fátima', tempo: 'Páscoa' },
  { id: '4', data: '2026-05-17', celebracao: '6º Domingo da Páscoa', tempo: 'Páscoa' },
];
