export const koreaProvinces = [
  {
    type: 'province',
    name: 'Gyeonggi-do',
    korean_name: '경기도',
    capital: 'Suwon',
    districts: [
      {
        name: 'Suwon-si',
        korean_name: '수원시',
        type: 'city',
        sub_districts: [
          { name: 'Jangan-gu', korean_name: '장안구', type: 'district' },
          { name: 'Gwonseon-gu', korean_name: '권선구', type: 'district' },
          { name: 'Paldal-gu', korean_name: '팔달구', type: 'district' },
          { name: 'Yeongtong-gu', korean_name: '영통구', type: 'district' },
        ],
      },
      {
        name: 'Seongnam-si',
        korean_name: '성남시',
        type: 'city',
        sub_districts: [
          { name: 'Sujeong-gu', korean_name: '수정구', type: 'district' },
          { name: 'Jungwon-gu', korean_name: '중원구', type: 'district' },
          { name: 'Bundang-gu', korean_name: '분당구', type: 'district' },
        ],
      },
      {
        name: 'Goyang-si',
        korean_name: '고양시',
        type: 'city',
        sub_districts: [
          { name: 'Deogyang-gu', korean_name: '덕양구', type: 'district' },
          { name: 'Ilsandong-gu', korean_name: '일산동구', type: 'district' },
          { name: 'Ilsanseo-gu', korean_name: '일산서구', type: 'district' },
        ],
      },
      {
        name: 'Yongin-si',
        korean_name: '용인시',
        type: 'city',
        sub_districts: [
          { name: 'Cheoin-gu', korean_name: '처인구', type: 'district' },
          { name: 'Giheung-gu', korean_name: '기흥구', type: 'district' },
          { name: 'Suji-gu', korean_name: '수지구', type: 'district' },
        ],
      },
      {
        name: 'Ansan-si',
        korean_name: '안산시',
        type: 'city',
        sub_districts: [
          { name: 'Sangnok-gu', korean_name: '상록구', type: 'district' },
          { name: 'Danwon-gu', korean_name: '단원구', type: 'district' },
        ],
      },
      {
        name: 'Yangpyeong-gun',
        korean_name: '양평군',
        type: 'county',
        sub_districts: [
          { name: 'Yangpyeong-eup', korean_name: '양평읍', type: 'town' },
          { name: 'Gaegun-myeon', korean_name: '개군면', type: 'township' },
          { name: 'Yangseo-myeon', korean_name: '양서면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'province',
    name: 'Gangwon-do',
    korean_name: '강원특별자치도',
    capital: 'Chuncheon',
    districts: [
      {
        name: 'Chuncheon-si',
        korean_name: '춘천시',
        type: 'city',
        sub_districts: [
          { name: 'Chuncheon-eup', korean_name: '춘천읍', type: 'town' },
          { name: 'Namsan-myeon', korean_name: '남산면', type: 'township' },
          {
            name: 'Seocho-dong',
            korean_name: '서초동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Wonju-si',
        korean_name: '원주시',
        type: 'city',
        sub_districts: [
          { name: 'Wonju-eup', korean_name: '원주읍', type: 'town' },
          { name: 'Munmak-eup', korean_name: '문막읍', type: 'town' },
          { name: 'Jijeong-myeon', korean_name: '지정면', type: 'township' },
        ],
      },
      {
        name: 'Gangneung-si',
        korean_name: '강릉시',
        type: 'city',
        sub_districts: [
          { name: 'Gangneung-eup', korean_name: '강릉읍', type: 'town' },
          { name: 'Okgye-myeon', korean_name: '옥계면', type: 'township' },
          { name: 'Jumunjin-eup', korean_name: '주문진읍', type: 'town' },
        ],
      },
    ],
  },
  {
    type: 'province',
    name: 'Chungcheongbuk-do',
    korean_name: '충청북도',
    capital: 'Cheongju',
    districts: [
      {
        name: 'Cheongju-si',
        korean_name: '청주시',
        type: 'city',
        sub_districts: [
          { name: 'Sangdang-gu', korean_name: '상당구', type: 'district' },
          { name: 'Seowon-gu', korean_name: '서원구', type: 'district' },
          { name: 'Heungdeok-gu', korean_name: '흥덕구', type: 'district' },
          { name: 'Cheongwon-gu', korean_name: '청원구', type: 'district' },
        ],
      },
      {
        name: 'Chungju-si',
        korean_name: '충주시',
        type: 'city',
        sub_districts: [
          { name: 'Chungju-eup', korean_name: '충주읍', type: 'town' },
          { name: 'Suanbo-myeon', korean_name: '수안보면', type: 'township' },
          { name: 'Salmi-myeon', korean_name: '살미면', type: 'township' },
        ],
      },
      {
        name: 'Jecheon-si',
        korean_name: '제천시',
        type: 'city',
        sub_districts: [
          { name: 'Jecheon-eup', korean_name: '제천읍', type: 'town' },
          { name: 'Bongyang-eup', korean_name: '봉양읍', type: 'town' },
          {
            name: 'Geumseong-myeon',
            korean_name: '금성면',
            type: 'township',
          },
        ],
      },
    ],
  },
  {
    type: 'province',
    name: 'Chungcheongnam-do',
    korean_name: '충청남도',
    capital: 'Hongseong',
    districts: [
      {
        name: 'Cheonan-si',
        korean_name: '천안시',
        type: 'city',
        sub_districts: [
          { name: 'Dongnam-gu', korean_name: '동남구', type: 'district' },
          { name: 'Seobuk-gu', korean_name: '서북구', type: 'district' },
        ],
      },
      {
        name: 'Asan-si',
        korean_name: '아산시',
        type: 'city',
        sub_districts: [
          { name: 'Asan-eup', korean_name: '아산읍', type: 'town' },
          { name: 'Baebang-eup', korean_name: '배방읍', type: 'town' },
          { name: 'Dogo-myeon', korean_name: '도고면', type: 'township' },
        ],
      },
      {
        name: 'Seosan-si',
        korean_name: '서산시',
        type: 'city',
        sub_districts: [
          { name: 'Seosan-eup', korean_name: '서산읍', type: 'town' },
          { name: 'Unsan-myeon', korean_name: '운산면', type: 'township' },
          { name: 'Buseok-myeon', korean_name: '부석면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'province',
    name: 'Jeollabuk-do',
    korean_name: '전북특별자치도',
    capital: 'Jeonju',
    districts: [
      {
        name: 'Jeonju-si',
        korean_name: '전주시',
        type: 'city',
        sub_districts: [
          { name: 'Wansan-gu', korean_name: '완산구', type: 'district' },
          { name: 'Deokjin-gu', korean_name: '덕진구', type: 'district' },
        ],
      },
      {
        name: 'Gunsan-si',
        korean_name: '군산시',
        type: 'city',
        sub_districts: [
          { name: 'Gunsan-eup', korean_name: '군산읍', type: 'town' },
          { name: 'Seongsan-myeon', korean_name: '성산면', type: 'township' },
          { name: 'Okgu-eup', korean_name: '옥구읍', type: 'town' },
        ],
      },
      {
        name: 'Iksan-si',
        korean_name: '익산시',
        type: 'city',
        sub_districts: [
          { name: 'Iksan-eup', korean_name: '익산읍', type: 'town' },
          { name: 'Hamna-eup', korean_name: '함나읍', type: 'town' },
          { name: 'Yongie-myeon', korean_name: '용안면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'province',
    name: 'Jeollanam-do',
    korean_name: '전라남도',
    capital: 'Muan',
    districts: [
      {
        name: 'Mokpo-si',
        korean_name: '목포시',
        type: 'city',
        sub_districts: [
          {
            name: 'Yeongsangang-dong',
            korean_name: '영산강동',
            type: 'neighborhood',
          },
          {
            name: 'Hadang-dong',
            korean_name: '하당동',
            type: 'neighborhood',
          },
          { name: 'Sanho-dong', korean_name: '산호동', type: 'neighborhood' },
        ],
      },
      {
        name: 'Yeosu-si',
        korean_name: '여수시',
        type: 'city',
        sub_districts: [
          { name: 'Yeosu-eup', korean_name: '여수읍', type: 'town' },
          { name: 'Dolsan-eup', korean_name: '돌산읍', type: 'town' },
          { name: 'Samil-dong', korean_name: '삼일동', type: 'neighborhood' },
        ],
      },
      {
        name: 'Suncheon-si',
        korean_name: '순천시',
        type: 'city',
        sub_districts: [
          { name: 'Suncheon-eup', korean_name: '순천읍', type: 'town' },
          { name: 'Haeryong-myeon', korean_name: '해룡면', type: 'township' },
          { name: 'Nagan-myeon', korean_name: '낙안면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'province',
    name: 'Gyeongsangbuk-do',
    korean_name: '경상북도',
    capital: 'Andong',
    districts: [
      {
        name: 'Pohang-si',
        korean_name: '포항시',
        type: 'city',
        sub_districts: [
          { name: 'Nam-gu', korean_name: '남구', type: 'district' },
          { name: 'Buk-gu', korean_name: '북구', type: 'district' },
        ],
      },
      {
        name: 'Gyeongju-si',
        korean_name: '경주시',
        type: 'city',
        sub_districts: [
          { name: 'Gyeongju-eup', korean_name: '경주읍', type: 'town' },
          { name: 'Angang-eup', korean_name: '안강읍', type: 'town' },
          { name: 'Gampo-eup', korean_name: '감포읍', type: 'town' },
        ],
      },
      {
        name: 'Andong-si',
        korean_name: '안동시',
        type: 'city',
        sub_districts: [
          { name: 'Andong-eup', korean_name: '안동읍', type: 'town' },
          { name: 'Pungsan-eup', korean_name: '풍산읍', type: 'town' },
          { name: 'Imdong-myeon', korean_name: '임동면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'province',
    name: 'Gyeongsangnam-do',
    korean_name: '경상남도',
    capital: 'Changwon',
    districts: [
      {
        name: 'Changwon-si',
        korean_name: '창원시',
        type: 'city',
        sub_districts: [
          { name: 'Uichang-gu', korean_name: '의창구', type: 'district' },
          { name: 'Seongsan-gu', korean_name: '성산구', type: 'district' },
          {
            name: 'Masanhappo-gu',
            korean_name: '마산합포구',
            type: 'district',
          },
          {
            name: 'Masanhoewon-gu',
            korean_name: '마산회원구',
            type: 'district',
          },
          { name: 'Jinhae-gu', korean_name: '진해구', type: 'district' },
        ],
      },
      {
        name: 'Jinju-si',
        korean_name: '진주시',
        type: 'city',
        sub_districts: [
          { name: 'Jinju-eup', korean_name: '진주읍', type: 'town' },
          { name: 'Jisu-myeon', korean_name: '지수면', type: 'township' },
          { name: 'Jinseong-myeon', korean_name: '진성면', type: 'township' },
        ],
      },
      {
        name: 'Gimhae-si',
        korean_name: '김해시',
        type: 'city',
        sub_districts: [
          { name: 'Jinyeong-eup', korean_name: '진영읍', type: 'town' },
          { name: 'Jangyu-myeon', korean_name: '장유면', type: 'township' },
          { name: 'Hallim-myeon', korean_name: '한림면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'province',
    name: 'Jeju-do',
    korean_name: '제주특별자치도',
    capital: 'Jeju City',
    districts: [
      {
        name: 'Jeju-si',
        korean_name: '제주시',
        type: 'city',
        sub_districts: [
          { name: 'Aewol-eup', korean_name: '애월읍', type: 'town' },
          { name: 'Hallim-eup', korean_name: '한림읍', type: 'town' },
          { name: 'Gujwa-eup', korean_name: '구좌읍', type: 'town' },
          { name: 'Jocheon-eup', korean_name: '조천읍', type: 'town' },
        ],
      },
      {
        name: 'Seogwipo-si',
        korean_name: '서귀포시',
        type: 'city',
        sub_districts: [
          { name: 'Namwon-eup', korean_name: '남원읍', type: 'town' },
          { name: 'Seongsan-eup', korean_name: '성산읍', type: 'town' },
          { name: 'Andeok-myeon', korean_name: '안덕면', type: 'township' },
          { name: 'Pyoseon-myeon', korean_name: '표선면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'special_city',
    name: 'Seoul',
    korean_name: '서울특별시',
    districts: [
      {
        name: 'Gangnam-gu',
        korean_name: '강남구',
        type: 'district',
        sub_districts: [
          {
            name: 'Apgujeong-dong',
            korean_name: '압구정동',
            type: 'neighborhood',
          },
          {
            name: 'Cheongdam-dong',
            korean_name: '청담동',
            type: 'neighborhood',
          },
          {
            name: 'Daechi-dong',
            korean_name: '대치동',
            type: 'neighborhood',
          },
          {
            name: 'Yeoksam-dong',
            korean_name: '역삼동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Gangdong-gu',
        korean_name: '강동구',
        type: 'district',
        sub_districts: [
          { name: 'Amsa-dong', korean_name: '암사동', type: 'neighborhood' },
          {
            name: 'Cheonho-dong',
            korean_name: '천호동',
            type: 'neighborhood',
          },
          { name: 'Gil-dong', korean_name: '길동', type: 'neighborhood' },
        ],
      },
      {
        name: 'Gangbuk-gu',
        korean_name: '강북구',
        type: 'district',
        sub_districts: [
          { name: 'Mia-dong', korean_name: '미아동', type: 'neighborhood' },
          { name: 'Suyu-dong', korean_name: '수유동', type: 'neighborhood' },
          { name: 'Ui-dong', korean_name: '우이동', type: 'neighborhood' },
        ],
      },
      {
        name: 'Mapo-gu',
        korean_name: '마포구',
        type: 'district',
        sub_districts: [
          { name: 'Hongdae', korean_name: '홍대', type: 'neighborhood' },
          {
            name: 'Hapjeong-dong',
            korean_name: '합정동',
            type: 'neighborhood',
          },
          {
            name: 'Yeonnam-dong',
            korean_name: '연남동',
            type: 'neighborhood',
          },
        ],
      },
    ],
  },
  {
    type: 'metropolitan_city',
    name: 'Busan',
    korean_name: '부산광역시',
    districts: [
      {
        name: 'Suyeong-gu',
        korean_name: '수영구',
        type: 'district',
        sub_districts: [
          {
            name: 'Gwangan-dong',
            korean_name: '광안동',
            type: 'neighborhood',
          },
          {
            name: 'Millak-dong',
            korean_name: '민락동',
            type: 'neighborhood',
          },
          {
            name: 'Namcheon-dong',
            korean_name: '남천동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Haeundae-gu',
        korean_name: '해운대구',
        type: 'district',
        sub_districts: [
          { name: 'Jung-dong', korean_name: '중동', type: 'neighborhood' },
          {
            name: 'Songjeong-dong',
            korean_name: '송정동',
            type: 'neighborhood',
          },
          {
            name: 'Banyeo-dong',
            korean_name: '반여동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Jung-gu',
        korean_name: '중구',
        type: 'district',
        sub_districts: [
          { name: 'Nampo-dong', korean_name: '남포동', type: 'neighborhood' },
          {
            name: 'Jungang-dong',
            korean_name: '중앙동',
            type: 'neighborhood',
          },
          {
            name: 'Gwangbok-dong',
            korean_name: '광복동',
            type: 'neighborhood',
          },
        ],
      },
    ],
  },
  {
    type: 'metropolitan_city',
    name: 'Incheon',
    korean_name: '인천광역시',
    districts: [
      {
        name: 'Jung-gu',
        korean_name: '중구',
        type: 'district',
        sub_districts: [
          { name: 'Sinpo-dong', korean_name: '신포동', type: 'neighborhood' },
          {
            name: 'Songwol-dong',
            korean_name: '송월동',
            type: 'neighborhood',
          },
          {
            name: 'Yeonsu-dong',
            korean_name: '연수동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Yeonsu-gu',
        korean_name: '연수구',
        type: 'district',
        sub_districts: [
          {
            name: 'Songdo-dong',
            korean_name: '송도동',
            type: 'neighborhood',
          },
          {
            name: 'Yeonsu-dong',
            korean_name: '연수동',
            type: 'neighborhood',
          },
          {
            name: 'Dongchun-dong',
            korean_name: '동춘동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Namdong-gu',
        korean_name: '남동구',
        type: 'district',
        sub_districts: [
          { name: 'Gojan-dong', korean_name: '고잔동', type: 'neighborhood' },
          { name: 'Mansu-dong', korean_name: '만수동', type: 'neighborhood' },
          {
            name: 'Nonhyeon-dong',
            korean_name: '논현동',
            type: 'neighborhood',
          },
        ],
      },
    ],
  },
  {
    type: 'metropolitan_city',
    name: 'Daegu',
    korean_name: '대구광역시',
    districts: [
      {
        name: 'Jung-gu',
        korean_name: '중구',
        type: 'district',
        sub_districts: [
          {
            name: 'Dongseong-ro',
            korean_name: '동성로',
            type: 'neighborhood',
          },
          {
            name: 'Seomun-dong',
            korean_name: '서문동',
            type: 'neighborhood',
          },
          {
            name: 'Namseong-dong',
            korean_name: '남성동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Suseong-gu',
        korean_name: '수성구',
        type: 'district',
        sub_districts: [
          {
            name: 'Beomeo-dong',
            korean_name: '범어동',
            type: 'neighborhood',
          },
          {
            name: 'Manchon-dong',
            korean_name: '만촌동',
            type: 'neighborhood',
          },
          {
            name: 'Suseong-dong',
            korean_name: '수성동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Dalseong-gun',
        korean_name: '달성군',
        type: 'county',
        sub_districts: [
          { name: 'Hwawon-eup', korean_name: '화원읍', type: 'town' },
          { name: 'Dasa-eup', korean_name: '다사읍', type: 'town' },
          { name: 'Okpo-myeon', korean_name: '옥포면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'metropolitan_city',
    name: 'Gwangju',
    korean_name: '광주광역시',
    districts: [
      {
        name: 'Dong-gu',
        korean_name: '동구',
        type: 'district',
        sub_districts: [
          {
            name: 'Dongmyeong-dong',
            korean_name: '동명동',
            type: 'neighborhood',
          },
          {
            name: 'Hwajeong-dong',
            korean_name: '화정동',
            type: 'neighborhood',
          },
          { name: 'Juwol-dong', korean_name: '주월동', type: 'neighborhood' },
        ],
      },
      {
        name: 'Seo-gu',
        korean_name: '서구',
        type: 'district',
        sub_districts: [
          {
            name: 'Yangsan-dong',
            korean_name: '양산동',
            type: 'neighborhood',
          },
          {
            name: 'Chipyeong-dong',
            korean_name: '치평동',
            type: 'neighborhood',
          },
          { name: 'Geumnam-ro', korean_name: '금남로', type: 'neighborhood' },
        ],
      },
      {
        name: 'Nam-gu',
        korean_name: '남구',
        type: 'district',
        sub_districts: [
          {
            name: 'Bongseon-dong',
            korean_name: '봉선동',
            type: 'neighborhood',
          },
          {
            name: 'Jinwol-dong',
            korean_name: '진월동',
            type: 'neighborhood',
          },
          {
            name: 'Seorim-dong',
            korean_name: '서림동',
            type: 'neighborhood',
          },
        ],
      },
    ],
  },
  {
    type: 'metropolitan_city',
    name: 'Daejeon',
    korean_name: '대전광역시',
    districts: [
      {
        name: 'Yuseong-gu',
        korean_name: '유성구',
        type: 'district',
        sub_districts: [
          {
            name: 'Bongmyeong-dong',
            korean_name: '봉명동',
            type: 'neighborhood',
          },
          {
            name: 'Guseong-dong',
            korean_name: '구성동',
            type: 'neighborhood',
          },
          {
            name: 'Jeonmin-dong',
            korean_name: '전민동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Seo-gu',
        korean_name: '서구',
        type: 'district',
        sub_districts: [
          {
            name: 'Dunsan-dong',
            korean_name: '둔산동',
            type: 'neighborhood',
          },
          { name: 'Galma-dong', korean_name: '갈마동', type: 'neighborhood' },
          {
            name: 'Mannyeon-dong',
            korean_name: '만년동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Jung-gu',
        korean_name: '중구',
        type: 'district',
        sub_districts: [
          {
            name: 'Daeheung-dong',
            korean_name: '대흥동',
            type: 'neighborhood',
          },
          {
            name: 'Eunhaeng-dong',
            korean_name: '은행동',
            type: 'neighborhood',
          },
          {
            name: 'Yongdu-dong',
            korean_name: '용두동',
            type: 'neighborhood',
          },
        ],
      },
    ],
  },
  {
    type: 'metropolitan_city',
    name: 'Ulsan',
    korean_name: '울산광역시',
    districts: [
      {
        name: 'Nam-gu',
        korean_name: '남구',
        type: 'district',
        sub_districts: [
          {
            name: 'Samsan-dong',
            korean_name: '삼산동',
            type: 'neighborhood',
          },
          { name: 'Dal-dong', korean_name: '달동', type: 'neighborhood' },
          { name: 'Mugeo-dong', korean_name: '무거동', type: 'neighborhood' },
        ],
      },
      {
        name: 'Jung-gu',
        korean_name: '중구',
        type: 'district',
        sub_districts: [
          { name: 'Yaeum-dong', korean_name: '야음동', type: 'neighborhood' },
          {
            name: 'Boksan-dong',
            korean_name: '복산동',
            type: 'neighborhood',
          },
          {
            name: 'Seongnam-dong',
            korean_name: '성남동',
            type: 'neighborhood',
          },
        ],
      },
      {
        name: 'Ulju-gun',
        korean_name: '울주군',
        type: 'county',
        sub_districts: [
          { name: 'Onyang-eup', korean_name: '온양읍', type: 'town' },
          { name: 'Eonyang-eup', korean_name: '언양읍', type: 'town' },
          { name: 'Samnam-myeon', korean_name: '삼남면', type: 'township' },
        ],
      },
    ],
  },
  {
    type: 'special_self_governing_city',
    name: 'Sejong',
    korean_name: '세종특별자치시',
    districts: [
      {
        name: 'Hansol-dong',
        korean_name: '한솔동',
        type: 'neighborhood',
        sub_districts: [],
      },
      {
        name: 'Dajeong-dong',
        korean_name: '다정동',
        type: 'neighborhood',
        sub_districts: [],
      },
      {
        name: 'Areum-dong',
        korean_name: '아름동',
        type: 'neighborhood',
        sub_districts: [],
      },
      {
        name: 'Jochiwon-eup',
        korean_name: '조치원읍',
        type: 'town',
        sub_districts: [],
      },
      {
        name: 'Bugang-myeon',
        korean_name: '부강면',
        type: 'township',
        sub_districts: [],
      },
    ],
  },
];
