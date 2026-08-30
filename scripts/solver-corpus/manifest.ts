// ==========================================================================
//
// Human-reviewed source manifest for the MCQ solver's PDF geometry corpus.
// The PDF files are fetched into an ignored cache; only checksums and derived,
// independently-reviewed facts are committed.
// ==========================================================================

export const SOLVER_GOLDEN_SCHEMA = 'solver-golden-corpus/v1' as const;

export const EXPECTED_SOLVER_PAPER_FAMILIES = [
  '0455/1',
  '0610/1', '0610/2',
  '0620/1', '0620/2',
  '0625/1', '0625/2',
  '0653/1', '0653/2',
  '0654/1', '0654/2',
  '2281/1',
  '5054/1', '5070/1', '5090/1',
  '9700/1', '9701/1', '9702/1', '9708/1',
] as const;

export type SolverCorpusSeries = 'm' | 's' | 'w';
export type SolverCorpusQualification = 'IGCSE' | 'AS/A Level' | 'O Level';
export type SolverOption = 'A' | 'B' | 'C' | 'D';
export type SolverBox = [x: number, y: number, x2: number, y2: number];

export interface SolverCorpusSource {
  file: string;
  sha256: string;
  bytes: number;
  pages: number;
}

export interface GeometryProbe {
  question: number;
  page: number;
  markers: Record<SolverOption, SolverBox>;
}

export interface OptionTextProbe {
  question: number;
  options: [string, string, string, string];
}

export interface KnownCorpusFailure {
  check: string;
  reason: string;
}

export interface SolverGoldenPaper {
  paperId: string;
  subjectCode: string;
  subject: string;
  qualification: SolverCorpusQualification;
  paperNumber: number;
  year: number;
  series: SolverCorpusSeries;
  variant: number;
  rationale: string[];
  sources: {
    questionPaper: SolverCorpusSource;
    markScheme: SolverCorpusSource;
  };
  expected: {
    questionCount: number;
    pageQuestionCounts: number[];
    answerKey: string;
    optionsPerQuestion: 4;
    geometryProbes: GeometryProbe[];
    optionTextProbes: OptionTextProbe[];
  };
  knownFailures: KnownCorpusFailure[];
}

export interface SolverGoldenCorpus {
  schemaVersion: typeof SOLVER_GOLDEN_SCHEMA;
  reviewedAt: string;
  sourceBaseUrl: string;
  reviewBasis: string[];
  papers: SolverGoldenPaper[];
}

const BASE = 'https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload';

function source(
  file: string,
  sha256: string,
  bytes: number,
  pages: number,
): SolverCorpusSource {
  return { file, sha256, bytes, pages };
}

export const SOLVER_GOLDEN_CORPUS: SolverGoldenCorpus = {
  schemaVersion: SOLVER_GOLDEN_SCHEMA,
  reviewedAt: '2026-08-30',
  sourceBaseUrl: BASE,
  reviewBasis: [
    'Question starts and page placement checked against Poppler layout extraction.',
    'Question totals and literal answer strings checked against the published mark schemes.',
    'Geometry probes checked at PDF viewport scale 1 against rendered source pages.',
    'Option-text probes transcribed from the rendered question paper, not parser output.',
  ],
  papers: [
    {
      paperId: '0455_w25_12', subjectCode: '0455', subject: 'Economics',
      qualification: 'IGCSE', paperNumber: 1, year: 2025, series: 'w', variant: 2,
      rationale: ['post-2016 support boundary', 'current economics layout', '30 questions'],
      sources: {
        questionPaper: source('0455_w25_qp_12.pdf', 'd08cf68665dea9a34a06cdf2f9a9d407dfb4dbdb2fbadb7b7c5ccee7ae6da520', 1055507, 12),
        markScheme: source('0455_w25_ms_12.pdf', 'e03d5e696c402186a3ecf4b06bb8e567321ebcaed2f82f95aa57b903ef211153', 167021, 3),
      },
      expected: {
        questionCount: 30,
        pageQuestionCounts: [0, 3, 2, 3, 3, 5, 4, 3, 2, 4, 1, 0],
        answerKey: 'DACCCBDDDBABCDDADCCCBCBDCACCBA', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '0610_w17_11', subjectCode: '0610', subject: 'Biology',
      qualification: 'IGCSE', paperNumber: 1, year: 2017, series: 'w', variant: 1,
      rationale: ['earliest supported year', 'Core biology layout', 'trailing blank page'],
      sources: {
        questionPaper: source('0610_w17_qp_11.pdf', '84569e97cf9de5489d3acd10f2a129f196ce5f3dcf2ffaad9f70874389b089a9', 411553, 16),
        markScheme: source('0610_w17_ms_11.pdf', '39b2a23cd6d5e84dc5ea9e8e4675c62683f7f71119b4c84045b4291a0a0b4e07', 84634, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 3, 2, 3, 6, 3, 4, 1, 1, 3, 3, 4, 4, 2, 1, 0],
        answerKey: 'BCBABBCCCCAABBCBBDDAAAABBACADBABBCDDCDDA', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '0610_s25_22', subjectCode: '0610', subject: 'Biology',
      qualification: 'IGCSE', paperNumber: 2, year: 2025, series: 's', variant: 2,
      rationale: ['current Extended layout', 'photograph question', 'horizontal options'],
      sources: {
        questionPaper: source('0610_s25_qp_22.pdf', '3cfb7c8c3f4cde791b60537b7df04589c161ce9113c9617bffb2de84dafc4339', 632042, 16),
        markScheme: source('0610_s25_ms_22.pdf', '2f4fe6c351c22150e48060034f15a8d6601991e39f2a69b553465127438a2f60', 168215, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 2, 4, 2, 1, 2, 3, 2, 3, 3, 3, 4, 4, 2, 2, 3],
        answerKey: 'CBDBCAACACBBBBDDDDCBCBCCDADDABBBCACCCDDD', optionsPerQuestion: 4,
        geometryProbes: [{ question: 1, page: 2, markers: {
          A: [70.9, 522.2, 78.8, 533.2], B: [170.1, 522.2, 178, 533.2],
          C: [269.4, 522.2, 277.3, 533.2], D: [368.6, 522.2, 376.5, 533.2],
        } }],
        optionTextProbes: [{ question: 1, options: ['A 1', 'B 2', 'C 3', 'D 4'] }],
      },
      knownFailures: [],
    },
    {
      paperId: '0620_m18_12', subjectCode: '0620', subject: 'Chemistry',
      qualification: 'IGCSE', paperNumber: 1, year: 2018, series: 'm', variant: 2,
      rationale: ['March Core layout', 'stacked fraction options', 'graph-font failure case'],
      sources: {
        questionPaper: source('0620_m18_qp_12.pdf', 'cbf2a61c4d53cfd7a6781339bb6825b3d2706241142621ecbfa8079fc55432f1', 267792, 16),
        markScheme: source('0620_m18_ms_12.pdf', '1a258357b433e1b5559ee0cf0d09c7220f7c2bae4d7849e5dc51a70db6f3489e', 83971, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 2, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 0, 0, 0, 0],
        answerKey: 'CBCDBCCACACABBBABBCDAABAABCBCCABCDDBCABB', optionsPerQuestion: 4,
        geometryProbes: [{ question: 8, page: 4, markers: {
          A: [70.9, 223.5, 78.9, 234.5], B: [70.9, 270.8, 78.9, 281.8],
          C: [70.9, 318.1, 78.9, 329], D: [70.9, 365.3, 78.9, 376.3],
        } }],
        optionTextProbes: [{ question: 8, options: ['A', 'B', 'C', 'D'] }],
      },
      knownFailures: [],
    },
    {
      paperId: '0620_w24_23', subjectCode: '0620', subject: 'Chemistry',
      qualification: 'IGCSE', paperNumber: 2, year: 2024, series: 'w', variant: 3,
      rationale: ['current Extended layout', 'dense table questions', 'variant 3'],
      sources: {
        questionPaper: source('0620_w24_qp_23.pdf', '574ceeb89a09f7a06876adb9e659dc21ec0a5a7e10d05d96d53efc5d65decc60', 334351, 16),
        markScheme: source('0620_w24_ms_23.pdf', 'cd255f06f780be89dc35619606aef72a3e6b021d6c39ed150c4f05fe88b57b3c', 169173, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 4, 4, 2, 3, 3, 3, 4, 4, 4, 4, 2, 3, 0, 0, 0],
        answerKey: 'CDBDBCBDACDCCADCADBAADACCBADBCDABADADCBA', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '0625_s18_11', subjectCode: '0625', subject: 'Physics',
      qualification: 'IGCSE', paperNumber: 1, year: 2018, series: 's', variant: 1,
      rationale: ['Core physics', 'ruler diagram', 'graph option grid'],
      sources: {
        questionPaper: source('0625_s18_qp_11.pdf', '9d03103ba94b9eaedd6438463218d275208065f9ebfe26fd857a508dfddd26d2', 225149, 16),
        markScheme: source('0625_s18_ms_11.pdf', 'e5dd53942589f92838b9278377074aeb1217805d6523e97c09b7c29fcd2086e8', 84353, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 3, 2, 2, 3, 4, 3, 4, 3, 3, 4, 2, 3, 3, 1, 0],
        answerKey: 'ADCBDCABDDACDCACBBBBABAABDCBACCDDBCCDDCC', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '0625_s24_22', subjectCode: '0625', subject: 'Physics',
      qualification: 'IGCSE', paperNumber: 2, year: 2024, series: 's', variant: 2,
      rationale: ['Extended physics', 'diagram plus table options', 'current mark-scheme format'],
      sources: {
        questionPaper: source('0625_s24_qp_22.pdf', '61e63622a9a06a85c2aa33751ae9a987b3daddc53fbaf72c1065bdafa695e477', 364463, 16),
        markScheme: source('0625_s24_ms_22.pdf', 'ec920bff63a4e638df1474d400074510112ff23c8dea61f57426d49463a7ea67', 96831, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 2, 3, 4, 3, 3, 3, 2, 2, 4, 4, 4, 2, 3, 1, 0],
        answerKey: 'CCBADDCBCADCBDADBADCCCBDADBDCAAAADBCAAAB', optionsPerQuestion: 4,
        geometryProbes: [{ question: 1, page: 2, markers: {
          A: [81.1, 324.5, 89, 335.5], B: [81.1, 345.5, 89, 356.5],
          C: [81.1, 366.5, 89, 377.5], D: [81.1, 387.5, 89, 398.5],
        } }],
        optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '0653_w19_11', subjectCode: '0653', subject: 'Combined Science',
      qualification: 'IGCSE', paperNumber: 1, year: 2019, series: 'w', variant: 1,
      rationale: ['mixed-discipline Core paper', 'lens diagram labels', 'duplicate marker failure'],
      sources: {
        questionPaper: source('0653_w19_qp_11.pdf', 'e25129666552baa3fa5227b98a49c0995ed58e3d8f85640da2c9319d450991c0', 416370, 16),
        markScheme: source('0653_w19_ms_11.pdf', 'aa6e23f984e7424bb71606a277aee3a4d8ccc15595b5c3083e01d4be4d85d854', 95139, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 3, 4, 3, 3, 3, 3, 4, 4, 2, 4, 2, 2, 3, 0, 0],
        answerKey: 'AABACABCDDBBDDDBDCBBCACDAACBDDDAABAABCDC', optionsPerQuestion: 4,
        geometryProbes: [{ question: 36, page: 13, markers: {
          A: [229.7, 263, 237.7, 274], B: [295.3, 264.9, 303.2, 275.9],
          C: [366.1, 262.8, 374, 273.8], D: [422.7, 319.5, 430.7, 330.5],
        } }],
        optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '0653_m25_22', subjectCode: '0653', subject: 'Combined Science',
      qualification: 'IGCSE', paperNumber: 2, year: 2025, series: 'm', variant: 2,
      rationale: ['current mixed-discipline Extended paper', 'March layout', 'six questions on one page'],
      sources: {
        questionPaper: source('0653_m25_qp_22.pdf', '40342a9d2660b80c10e45ce1f2331517a640a63fb42e2879131f8e2a3a5200ef', 386530, 16),
        markScheme: source('0653_m25_ms_22.pdf', '8605ac13a22052b608c23bdb170447d9c06cba61d2d9f717f89c00cf16e983dc', 168812, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 3, 3, 3, 4, 5, 2, 1, 2, 2, 3, 3, 3, 6, 0, 0],
        answerKey: 'BDBCCBADABAACDCDACDBBCBADCACDDCABDABCABD', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '0654_w18_11', subjectCode: '0654', subject: 'Co-ordinated Sciences',
      qualification: 'IGCSE', paperNumber: 1, year: 2018, series: 'w', variant: 1,
      rationale: ['Core co-ordinated science', 'cell diagrams', 'older typography'],
      sources: {
        questionPaper: source('0654_w18_qp_11.pdf', '1fd4f34aa76ffc3462e7cc1b803ff241326a176b03abbc47081ff9a9bf98714e', 397112, 16),
        markScheme: source('0654_w18_ms_11.pdf', '5de04de461a199a7f959d0a5ca30d6e9ecb1fb78281e22c08a376a77859e038e', 84285, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 4, 2, 3, 2, 3, 3, 3, 3, 3, 2, 3, 3, 4, 2, 0],
        answerKey: 'CACAACBCDCCBDBDADDBCBCACDBCCDBAAABACDDCD', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '0654_s25_23', subjectCode: '0654', subject: 'Co-ordinated Sciences',
      qualification: 'IGCSE', paperNumber: 2, year: 2025, series: 's', variant: 3,
      rationale: ['current Extended co-ordinated science', 'embedded font warning', 'variant 3'],
      sources: {
        questionPaper: source('0654_s25_qp_23.pdf', '4743716817952768651990575442086472ac0076f04e37562f9dafe5c1d234c1', 362819, 16),
        markScheme: source('0654_s25_ms_23.pdf', '48f8af76a6139cb317d913653aa03056ee74e6c92f8d4f30359241e553eea9fa', 169128, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 3, 3, 4, 3, 3, 3, 4, 3, 4, 3, 4, 3, 0, 0, 0],
        answerKey: 'BAABCCCABCDDCABCCBDCDADBBBCBCADADDBCCACA', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '9700_w25_13', subjectCode: '9700', subject: 'Biology',
      qualification: 'AS/A Level', paperNumber: 1, year: 2025, series: 'w', variant: 3,
      rationale: ['post-2016 support boundary', 'current A-Level biology layout', 'trailing blank pages'],
      sources: {
        questionPaper: source('9700_w25_qp_13.pdf', 'b5a43e15470755645e08cbc53079c5733cdec6da71ab1bbe93c9a50a737aa316', 2006131, 20),
        markScheme: source('9700_w25_ms_13.pdf', '5c1be4aa9b40059c1cce2bf447f13582e5a40a3750c81eaa643807ad50e57c97', 170782, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 2, 2, 2, 3, 4, 3, 3, 3, 2, 2, 1, 2, 3, 3, 2, 1, 2, 0, 0],
        answerKey: 'BBCCBBBCABAAABCDADACDDCDBBACDACCCDABABAB', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '9701_m25_12', subjectCode: '9701', subject: 'Chemistry',
      qualification: 'AS/A Level', paperNumber: 1, year: 2025, series: 'm', variant: 2,
      rationale: ['current A-Level chemistry', 'spatial graph labels', 'content-stream ordering regression'],
      sources: {
        questionPaper: source('9701_m25_qp_12.pdf', 'c8de72e379c78d9eabf65abd52323bd7a31af2c3b3872e50e2a941a4bfe59f99', 415854, 20),
        markScheme: source('9701_m25_ms_12.pdf', '66d630d79803daa9e4fed12a768b2ab8068229750293611af2426ec3c6f19286', 131611, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 2, 3, 1, 0, 0, 0, 0, 0],
        answerKey: 'DDCBACACDABABBCADCBABABCADCBCDBCCCBDBADD', optionsPerQuestion: 4,
        geometryProbes: [{ question: 1, page: 2, markers: {
          A: [360.7, 250.4, 368.6, 261.3], B: [390, 234.7, 398, 245.7],
          C: [405, 250.4, 413, 261.3], D: [390, 265.1, 398, 276.1],
        } }],
        optionTextProbes: [{ question: 1, options: ['A', 'B', 'C', 'D'] }],
      },
      knownFailures: [],
    },
    {
      paperId: '9702_s24_12', subjectCode: '9702', subject: 'Physics',
      qualification: 'AS/A Level', paperNumber: 1, year: 2024, series: 's', variant: 2,
      rationale: ['A-Level physics', 'two cover pages', 'mixed graph and table options'],
      sources: {
        questionPaper: source('9702_s24_qp_12.pdf', '28c2b3e6acd199243879d9a80e05417a0f1b7c664aa33004fbedb5a493fbad1d', 395895, 16),
        markScheme: source('9702_s24_ms_12.pdf', '246a8612284b9ca42ef52b38f54ebdd39fbbc670bebc34d92786d0c1c60f9921', 96260, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 0, 4, 2, 3, 2, 3, 3, 2, 2, 2, 4, 3, 4, 3, 3],
        answerKey: 'CDADBBCACABCDCDABCCDCDBBCADDACDCBADABDCC', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '9708_s25_13', subjectCode: '9708', subject: 'Economics',
      qualification: 'AS/A Level', paperNumber: 1, year: 2025, series: 's', variant: 3,
      rationale: ['current A-Level economics', '30 questions', 'option-text association regression'],
      sources: {
        questionPaper: source('9708_s25_qp_13.pdf', '0632473d45e5b44068127ab5128be01ade0a1b46d067e296fec5fcf4b7cdb871', 1027701, 12),
        markScheme: source('9708_s25_ms_13.pdf', 'bed320f02caa38740affee280b23d73f07840d77e509be53654aad84672ca4f7', 164977, 3),
      },
      expected: {
        questionCount: 30,
        pageQuestionCounts: [0, 3, 3, 2, 4, 2, 1, 3, 4, 4, 3, 1],
        answerKey: 'DCBDABABBCCACDCABCACBDADBDABAB', optionsPerQuestion: 4,
        geometryProbes: [],
        optionTextProbes: [{ question: 1, options: [
          'A a free good', 'B an inferior good', 'C a public good', 'D a private good',
        ] }],
      },
      knownFailures: [],
    },
    {
      paperId: '5090_s25_11', subjectCode: '5090', subject: 'Biology',
      qualification: 'O Level', paperNumber: 1, year: 2025, series: 's', variant: 1,
      rationale: ['post-2016 support boundary', 'current O-Level biology layout', 'trailing blank pages'],
      sources: {
        questionPaper: source('5090_s25_qp_11.pdf', '17751a57ae673fa37206570022ba9338d4819c84ff91b4da841cc815aed2a1ef', 1434210, 20),
        markScheme: source('5090_s25_ms_11.pdf', 'ff18e169485ef76973f722d36bce20451857aefade63413c7bbcf380c7274c48', 166209, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 2, 2, 3, 2, 2, 1, 1, 2, 3, 2, 3, 2, 3, 5, 4, 3, 0, 0, 0],
        answerKey: 'DBBBBADADBCADCDCCCBBCACADBABBCBBBCCDDDBD', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '5070_w25_12', subjectCode: '5070', subject: 'Chemistry',
      qualification: 'O Level', paperNumber: 1, year: 2025, series: 'w', variant: 2,
      rationale: ['current O-Level chemistry', 'table options', 'November variant 2'],
      sources: {
        questionPaper: source('5070_w25_qp_12.pdf', 'ebadb2c89ad7d9abb56485cdf8e6b63225a6629020f3e2e04a7baa1b4314da99', 320630, 16),
        markScheme: source('5070_w25_ms_12.pdf', 'aad9447c861dff1a70205c0ea0bdf3a9e867626b4d58d6b230b473795ad0fdd4', 169306, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 4, 4, 2, 2, 3, 2, 4, 4, 4, 4, 2, 2, 3, 0, 0],
        answerKey: 'CDBDACBACACCCAAAACBBBDDDDDBCACBDDDDABADA', optionsPerQuestion: 4,
        geometryProbes: [], optionTextProbes: [],
      },
      knownFailures: [],
    },
    {
      paperId: '5054_w18_12', subjectCode: '5054', subject: 'Physics',
      qualification: 'O Level', paperNumber: 1, year: 2018, series: 'w', variant: 2,
      rationale: ['O-Level physics', 'table-column option labels', 'eight-option regression'],
      sources: {
        questionPaper: source('5054_w18_qp_12.pdf', '32496c6c80ae8e4e233edf39611fe0f82a68569f744f6b359d859365e82d003c', 290143, 16),
        markScheme: source('5054_w18_ms_12.pdf', '7ece1760daf941d61a72de9a18a4e4a5469fda4a19c4b16f6626690be9d5f88d', 83199, 3),
      },
      expected: {
        questionCount: 40,
        pageQuestionCounts: [0, 3, 3, 2, 2, 2, 3, 3, 2, 4, 4, 3, 3, 3, 3, 0],
        answerKey: 'CABBADCDBADCDBBCADCCBCAADCDBDDDCACDABCDB', optionsPerQuestion: 4,
        geometryProbes: [{ question: 2, page: 2, markers: {
          A: [172.3, 313.7, 180.2, 324.7], B: [245.7, 313.7, 253.6, 324.7],
          C: [319.6, 313.7, 327.6, 324.7], D: [393, 313.7, 400.9, 324.7],
        } }],
        optionTextProbes: [{ question: 2, options: ['A', 'B', 'C', 'D'] }],
      },
      knownFailures: [],
    },
    {
      paperId: '2281_w25_13', subjectCode: '2281', subject: 'Economics',
      qualification: 'O Level', paperNumber: 1, year: 2025, series: 'w', variant: 3,
      rationale: ['current O-Level economics', '30 questions', 'stream-order association and inline-letter failures'],
      sources: {
        questionPaper: source('2281_w25_qp_13.pdf', 'e0e3036edf1a41bd9f38b4be70af4ecb798eb3ef7bef4b8300464ff4f447bc09', 1419802, 12),
        markScheme: source('2281_w25_ms_13.pdf', '4b84cac2f676009faa165f0c97726947063d2372176c27700813c3352d6033ba', 165465, 3),
      },
      expected: {
        questionCount: 30,
        pageQuestionCounts: [0, 4, 2, 4, 4, 4, 4, 3, 4, 1, 0, 0],
        answerKey: 'DBDADCADCCDBABDBABBCCCCDBBDCCB', optionsPerQuestion: 4,
        geometryProbes: [{ question: 1, page: 2, markers: {
          A: [72.3, 87.7, 80.2, 98.7], B: [72.3, 109.4, 80.2, 120.4],
          C: [72.3, 131.1, 80.2, 142.1], D: [72.3, 152.8, 80.2, 163.8],
        } }],
        optionTextProbes: [{ question: 1, options: [
          'A greater provision of information about available jobs',
          'B improved roads and communication network',
          'C increased opportunities for education and training',
          'D strengthened family ties and relationships',
        ] }],
      },
      knownFailures: [],
    },
  ],
};

export async function loadSolverGoldenCorpus(): Promise<SolverGoldenCorpus> {
  return SOLVER_GOLDEN_CORPUS;
}

export function validateSolverGoldenCorpus(corpus: SolverGoldenCorpus): string[] {
  const errors: string[] = [];
  const ids = new Set<string>();
  const sha256 = /^[a-f0-9]{64}$/;

  if (corpus.schemaVersion !== SOLVER_GOLDEN_SCHEMA) {
    errors.push(`unsupported schema ${corpus.schemaVersion}`);
  }

  for (const paper of corpus.papers) {
    if (ids.has(paper.paperId)) errors.push(`${paper.paperId}: duplicate paper id`);
    ids.add(paper.paperId);

    if (!/^[0-9]{4}_[msw][0-9]{2}_[0-9]{2}$/.test(paper.paperId)) {
      errors.push(`${paper.paperId}: invalid paper id`);
    }
    if (!/^[ABCD]+$/.test(paper.expected.answerKey)) {
      errors.push(`${paper.paperId}: answer key contains a non-option character`);
    }
    if (paper.expected.answerKey.length !== paper.expected.questionCount) {
      errors.push(`${paper.paperId}: answer key length does not match question count`);
    }
    if (paper.expected.pageQuestionCounts.length !== paper.sources.questionPaper.pages) {
      errors.push(`${paper.paperId}: page counts do not cover every PDF page`);
    }
    if (paper.expected.pageQuestionCounts.reduce((sum, count) => sum + count, 0)
        !== paper.expected.questionCount) {
      errors.push(`${paper.paperId}: page question counts do not sum to the paper total`);
    }

    for (const item of Object.values(paper.sources)) {
      if (!sha256.test(item.sha256)) errors.push(`${paper.paperId}: invalid SHA-256 for ${item.file}`);
      if (item.bytes <= 0) errors.push(`${paper.paperId}: empty source ${item.file}`);
      if (item.pages <= 0) errors.push(`${paper.paperId}: invalid page count for ${item.file}`);
    }

    for (const probe of paper.expected.geometryProbes) {
      if (probe.question < 1 || probe.question > paper.expected.questionCount) {
        errors.push(`${paper.paperId}: geometry probe question ${probe.question} is out of range`);
      }
      for (const option of ['A', 'B', 'C', 'D'] as const) {
        const [x, y, x2, y2] = probe.markers[option];
        if (!(x2 > x && y2 > y)) {
          errors.push(`${paper.paperId}: invalid ${option} geometry for question ${probe.question}`);
        }
      }
    }
  }

  return errors;
}
