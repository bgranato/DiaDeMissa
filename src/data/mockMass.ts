import { Mass, UserReminder, HistoryItem } from '../types/mass';

export const MOCK_MASS: Mass = {
  id: '2026-05-10-mass',
  data: "2026-05-10",
  celebracao: "6º Domingo da Páscoa",
  tempo_liturgico: "Páscoa",
  resumo: "Jesus nos convida a permanecer no seu amor. Amar uns aos outros como Ele nos amou é a alegria plena que o Senhor nos oferece.",
  blocos: [
    {
      ordem: 1,
      tipo: "canto_entrada",
      titulo: "Canto de Entrada",
      conteudo: "Cantai ao Senhor um cântico novo, Aleluia! Pois ele fez maravilhas, Aleluia! \n\nAnunciai com brado de alegria, fazei que se ouça, anunciai até os confins da terra: o Senhor libertou o seu povo. Aleluia! \n\nVinde, exultemos de alegria no Senhor, aclamemos o Rock da nossa salvação! Vamos à sua presença com hinos de louvor."
    },
    {
      ordem: 2,
      tipo: "ato_penitencial",
      titulo: "Ato Penitencial",
      conteudo: "Senhor, que viestes procurar quem estava perdido, tende piedade de nós. \n\nSenhor, tende piedade de nós. \n\nCristo, que destes a vida para reunir os filhos de Deus dispersos, tende piedade de nós. \n\nCristo, tende piedade de nós. \n\nSenhor, que intercedeis por nós junto do Pai, tende piedade de nós. \n\nSenhor, tende piedade de nós."
    },
    {
      ordem: 3,
      tipo: "oracao_dia",
      titulo: "Oração do Dia",
      conteudo: "Deus onipotente, dai-nos celebrar com fervor estes dias de alegria em honra do Senhor ressuscitado, para que a nossa vida manifeste sempre o mistério que celebramos. Por nosso Senhor Jesus Cristo, vosso Filho, na unidade do Espírito Santo."
    },
    {
      ordem: 4,
      tipo: "primeira_leitura",
      titulo: "Primeira Leitura",
      referencia: "At 10, 25-26. 34-35. 44-48",
      conteudo: "Quando Pedro estava para entrar, Cornélio saiu à sua frente, caiu a seus pés e prostrou-se. Mas Pedro levantou-o, dizendo: 'Levanta-te, eu também sou apenas um homem'. \n\nPedro tomou a palavra e disse: 'De fato, estou compreendendo que Deus não faz distinção entre as pessoas. Pelo contrário, ele aceita quem o teme e pratica a justiça, qualquer que seja a nação a que pertença'. \n\nPedro ainda estava falando, quando o Espírito Santo desceu sobre todos os que ouviam a palavra."
    },
    {
      ordem: 5,
      tipo: "salmo_responsorial",
      titulo: "Salmo Responsorial",
      referencia: "Sl 97(98)",
      conteudo: "R. O Senhor fez conhecer a sua salvação e às nações revelou sua justiça.\n\nCantai ao Senhor um cântico novo, porque ele fez prodígios. Sua mão e seu braço santo alcançaram-lhe a vitória.\n\nO Senhor fez conhecer a sua salvação, revelou sua justiça às nações. Recordou-se da sua bondade e fidelidade em favor da casa de Israel."
    },
    {
      ordem: 6,
      tipo: "segunda_leitura",
      titulo: "Segunda Leitura",
      referencia: "1Jo 4, 7-10",
      conteudo: "Caríssimos, amemo-nos uns aos outros, porque o amor vem de Deus e todo aquele que ama nasceu de Deus e conhece a Deus. Quem não ama não chegou a conhecer a Deus, pois Deus é amor. \n\nFoi assim que se manifestou o amor de Deus para conosco: Deus enviou o seu Filho único ao mundo, para que por ele tenhamos a vida."
    },
    {
      ordem: 7,
      tipo: "evangelho",
      titulo: "Evangelho",
      referencia: "Jo 15, 9-17",
      conteudo: "Naquele tempo, disse Jesus aos seus discípulos: 'Como meu Pai me amou, assim também eu vos amei. Permanecei no meu amor. Se guardardes os meus mandamentos, permanecereis no meu amor, assim como eu guardei os mandamentos de meu Pai e permaneço no seu amor. \n\nEu vos disse isto, para que a minha alegria esteja em vós e a vossa alegria seja plena. Este é o meu mandamento: amai-vos uns aos outros, assim como eu vos amei'."
    },
    {
      ordem: 8,
      tipo: "comunhao",
      titulo: "Comunhão",
      conteudo: "Se vós me amais, guardareis os meus mandamentos, diz o Senhor. E eu rogarei ao Pai e ele vos dará um outro Defensor, para que permaneça sempre convosco. Aleluia! \n\nNinguém tem maior amor do que aquele que dá a vida pelos seus amigos. Vós sois meus amigos, se fizerdes o que eu vos mando."
    },
    {
      ordem: 9,
      tipo: "bencao_final",
      titulo: "Bênção Final",
      conteudo: "O Senhor esteja convosco. \nEle está no meio de nós. \n\nAbençoe-vos Deus todo-poderoso, Pai e Filho e Espírito Santo. \nAmém. \n\nIde em paz e o Senhor vos acompanhe. Aleluia, Aleluia! \nGraças a Deus. Aleluia, Aleluia!"
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
